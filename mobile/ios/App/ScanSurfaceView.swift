import SwiftUI
import SceneKit
import OpenSourceOrthoLiteKit

/// Synchronized real surfaces. The mask reveals observations; it never morphs geometry.
struct ScanSurfaceView: UIViewRepresentable {
    let presentation: ScanPresentation
    let progress: Double
    let resetID: Int
    func makeUIView(context: Context) -> ScanCanvas { ScanCanvas() }
    func updateUIView(_ view: ScanCanvas, context: Context) {
        view.update(presentation, progress: progress, reset: resetID)
    }
}

final class ScanCanvas: UIView {
    private let baseline = SCNView(), followup = SCNView()
    private let reveal = CALayer(), divider = CALayer()
    private var signature = ""
    private var resetID = -1
    private var progress = 0.0
    private var compared = false
    private var groups: [SCNNode] = []
    private var cameras: [SCNNode] = []
    private var yaw: Float = 0, pitch: Float = -0.12
    private var zoom = 1.0
    private var baseScale = 1.3

    init() {
        super.init(frame: .zero)
        for view in [baseline, followup] {
            view.backgroundColor = UIColor(red: 0.065, green: 0.09, blue: 0.14, alpha: 1)
            view.antialiasingMode = .multisampling4X
            view.isUserInteractionEnabled = false
            addSubview(view)
        }
        reveal.backgroundColor = UIColor.white.cgColor
        followup.layer.mask = reveal
        divider.backgroundColor = UIColor.systemCyan.cgColor
        layer.addSublayer(divider)
        addGestureRecognizer(UIPanGestureRecognizer(target: self, action: #selector(pan(_:))))
        addGestureRecognizer(UIPinchGestureRecognizer(target: self, action: #selector(pinch(_:))))
        accessibilityLabel = "Recorded scan surfaces. Drag to rotate; pinch to zoom."
    }
    required init?(coder: NSCoder) { fatalError("Programmatic view") }

    func update(_ presentation: ScanPresentation, progress: Double, reset: Int) {
        let key = (presentation.before + presentation.after).map(\.id).joined(separator: ":")
        if signature != key {
            signature = key; groups = []; cameras = []
            compared = !presentation.after.isEmpty
            baseScale = presentation.before.count > 1 ? 2.0 : 1.25
            baseline.scene = makeScene(presentation.before)
            followup.scene = compared ? makeScene(presentation.after) : nil
            baseline.pointOfView = cameras.first
            followup.pointOfView = compared ? cameras.last : nil
            yaw = 0; pitch = -0.12; zoom = 1
        }
        if resetID != reset { resetID = reset; yaw = 0; pitch = -0.12; zoom = 1 }
        self.progress = compared ? min(1, max(0, progress)) : 0
        applyCamera()
        setNeedsLayout()
    }

    override func layoutSubviews() {
        super.layoutSubviews()
        baseline.frame = bounds; followup.frame = bounds
        let x = bounds.width * (1 - progress)
        CATransaction.begin(); CATransaction.setDisableActions(true)
        reveal.frame = CGRect(x: x, y: 0, width: bounds.width-x, height: bounds.height)
        divider.frame = CGRect(x: x-1, y: 0, width: 2, height: bounds.height)
        divider.isHidden = !compared || progress == 0 || progress == 1
        CATransaction.commit()
        applyCamera()
    }

    private func makeScene(_ layers: [ScanLayer]) -> SCNScene {
        let scene = SCNScene()
        for (index, layer) in layers.enumerated() {
            let data = layer.mesh.vertices.withUnsafeBufferPointer { Data(buffer: $0) }
            let sources = [SCNGeometrySource.Semantic.vertex, .normal].enumerated().map { offset, semantic in
                SCNGeometrySource(data: data, semantic: semantic, vectorCount: layer.mesh.vertexCount,
                                  usesFloatComponents: true, componentsPerVector: 3, bytesPerComponent: 4,
                                  dataOffset: offset*12, dataStride: 24)
            }
            let element = SCNGeometryElement(data: nil, primitiveType: layer.mesh.isPointCloud ? .point : .triangles,
                                            primitiveCount: layer.mesh.isPointCloud ? layer.mesh.vertexCount : layer.mesh.triangleCount, bytesPerIndex: 4)
            element.pointSize = 2; element.minimumPointScreenSpaceRadius = 1; element.maximumPointScreenSpaceRadius = 3
            let geometry = SCNGeometry(sources: sources, elements: [element])
            let material = SCNMaterial()
            material.diffuse.contents = UIColor(red: 0.83, green: 0.85, blue: 0.88, alpha: 1)
            material.lightingModel = layer.mesh.isPointCloud ? .constant : .physicallyBased
            material.roughness.contents = 0.7
            material.metalness.contents = 0
            material.isDoubleSided = true
            geometry.materials = [material]
            let surface = SCNNode(geometry: geometry)
            let c = layer.mesh.center
            surface.position = SCNVector3(-c[0], -c[1], -c[2])
            let orient = SCNNode(); orient.addChildNode(surface)
            let scale: Float = (layers.count > 1 ? 1.65 : 2) / layer.mesh.span
            orient.scale = SCNVector3(scale*layer.rotation[0], scale*layer.rotation[1], scale*layer.rotation[2])
            let pivot = SCNNode(); pivot.addChildNode(orient)
            pivot.position.y = layers.count > 1 ? (index == 0 ? 0.95 : -0.95) : 0
            groups.append(pivot); scene.rootNode.addChildNode(pivot)
        }
        let camera = SCNNode(); camera.camera = SCNCamera()
        camera.camera?.usesOrthographicProjection = true
        camera.camera?.zNear = 0.01; camera.camera?.zFar = 100
        camera.position = SCNVector3(0,0,5)
        scene.rootNode.addChildNode(camera); cameras.append(camera)
        light(scene, .ambient, 230, SCNVector3Zero)
        light(scene, .directional, 850, SCNVector3(-0.5,-0.45,0))
        light(scene, .directional, 350, SCNVector3(0.3,0.8,0))
        return scene
    }

    private func light(_ scene: SCNScene, _ type: SCNLight.LightType, _ intensity: CGFloat, _ angles: SCNVector3) {
        let node = SCNNode(); node.light = SCNLight(); node.light?.type = type
        node.light?.intensity = intensity; node.eulerAngles = angles; scene.rootNode.addChildNode(node)
    }
    private func applyCamera() {
        for group in groups { group.eulerAngles = SCNVector3(pitch,yaw,0) }
        let aspect = max(0.1, bounds.width / max(1,bounds.height))
        for camera in cameras { camera.camera?.orthographicScale = max(baseScale, 1.1 / aspect) / zoom }
    }
    @objc private func pan(_ gesture: UIPanGestureRecognizer) {
        let delta = gesture.translation(in: self)
        yaw += Float(delta.x)*0.008; pitch += Float(delta.y)*0.008
        gesture.setTranslation(.zero, in: self); applyCamera()
    }
    @objc private func pinch(_ gesture: UIPinchGestureRecognizer) {
        zoom = min(4, max(0.5, zoom*gesture.scale)); gesture.scale = 1; applyCamera()
    }
}
