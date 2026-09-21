import SwiftUI
import SceneKit
import OpenSourceOrthoLiteKit

/// One complete observed surface, independently centered for inspection.
struct ScanSurfaceView: UIViewRepresentable {
    let mesh: STLMesh
    let rotation: [Float]
    let resetID: Int

    func makeUIView(context: Context) -> SCNView {
        let view = SCNView()
        view.backgroundColor = UIColor(red: 0.07, green: 0.10, blue: 0.15, alpha: 1)
        view.allowsCameraControl = true
        view.autoenablesDefaultLighting = false
        view.antialiasingMode = .multisampling4X
        view.accessibilityLabel = "Real STL scan. Drag to rotate and pinch to zoom."
        return view
    }

    func updateUIView(_ view: SCNView, context: Context) {
        // Parent recreates this view only when the selected scan or reset changes.
        guard view.scene == nil || context.coordinator.resetID != resetID else { return }
        context.coordinator.resetID = resetID
        let scene = SCNScene()
        let data = mesh.vertices.withUnsafeBufferPointer { Data(buffer: $0) }
        let sources = [SCNGeometrySource.Semantic.vertex, .normal].enumerated().map { index, semantic in
            SCNGeometrySource(data: data, semantic: semantic, vectorCount: mesh.triangleCount * 3,
                              usesFloatComponents: true, componentsPerVector: 3, bytesPerComponent: 4,
                              dataOffset: index * 12, dataStride: 24)
        }
        let element = SCNGeometryElement(data: nil, primitiveType: .triangles,
                                        primitiveCount: mesh.triangleCount, bytesPerIndex: 4)
        let geometry = SCNGeometry(sources: sources, elements: [element])
        let material = SCNMaterial()
        material.diffuse.contents = UIColor(red: 0.88, green: 0.85, blue: 0.78, alpha: 1)
        material.lightingModel = .physicallyBased
        material.roughness.contents = 0.8
        material.metalness.contents = 0
        material.isDoubleSided = true
        geometry.materials = [material]
        let surface = SCNNode(geometry: geometry)
        surface.position = SCNVector3(-mesh.center[0], -mesh.center[1], -mesh.center[2])
        let group = SCNNode()
        group.addChildNode(surface)
        let scale = 2 / mesh.span
        group.scale = SCNVector3(scale * rotation[0], scale * rotation[1], scale * rotation[2])
        scene.rootNode.addChildNode(group)
        let camera = SCNNode()
        camera.camera = SCNCamera()
        camera.camera?.usesOrthographicProjection = true
        camera.camera?.orthographicScale = 1.3
        camera.camera?.zNear = 0.01
        camera.camera?.zFar = 100
        camera.position = SCNVector3(0, 0, 5)
        scene.rootNode.addChildNode(camera)
        addLight(to: scene, type: .ambient, intensity: 350, angles: SCNVector3Zero)
        addLight(to: scene, type: .directional, intensity: 800, angles: SCNVector3(-0.4, -0.4, 0))
        view.scene = scene
        view.pointOfView = camera
        view.defaultCameraController.target = SCNVector3Zero
        view.defaultCameraController.interactionMode = .orbitTurntable
    }

    private func addLight(to scene: SCNScene, type: SCNLight.LightType, intensity: CGFloat, angles: SCNVector3) {
        let node = SCNNode()
        node.light = SCNLight()
        node.light?.type = type
        node.light?.intensity = intensity
        node.eulerAngles = angles
        scene.rootNode.addChildNode(node)
    }

    final class Coordinator { var resetID = -1 }
    func makeCoordinator() -> Coordinator { Coordinator() }
}
