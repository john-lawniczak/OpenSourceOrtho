import SwiftUI
import OpenSourceOrthoLiteKit

// Lite-flow screens. These are scaffolding: they wire the flow and render engine
// output. The STL file picker and the real 3D renderer are marked TODO - see
// ../README.md "What still has to be built".

/// Step 1: pick an STL scan from the device.
struct UploadView: View {
    @EnvironmentObject private var model: LiteFlowViewModel

    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "square.and.arrow.up")
                .font(.system(size: 48))
                .foregroundStyle(.tint)
            Text("Upload an STL scan")
                .font(.title3.bold())
            Text("Choose an upper and/or lower arch scan from your device.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
            // TODO: present `.fileImporter` for .stl and register bytes with the
            // engine mesh workspace. For scaffolding we stub a selected scan.
            Button("Choose STL file") {
                model.addScan(SelectedScan(fileName: "upper.stl", arch: "upper", byteCount: 0))
            }
            .buttonStyle(.borderedProminent)
        }
        .padding()
        .frame(maxHeight: .infinity)
    }
}

/// Step 2: one-tap generate.
struct GenerateView: View {
    @EnvironmentObject private var model: LiteFlowViewModel

    var body: some View {
        VStack(spacing: 16) {
            Text("\(model.scans.count) scan(s) selected")
                .font(.headline)
            if let error = model.errorMessage {
                Text(error).font(.footnote).foregroundStyle(.red).multilineTextAlignment(.center)
            }
            Button {
                Task { await model.generate() }
            } label: {
                if model.isGenerating { ProgressView() } else { Text("Generate plan") }
            }
            .buttonStyle(.borderedProminent)
            .disabled(model.isGenerating)
        }
        .padding()
        .frame(maxHeight: .infinity)
    }
}

/// Step 3: engine verdict + steps. Verdict is CONSISTENT/ISSUES only.
struct ReviewView: View {
    @EnvironmentObject private var model: LiteFlowViewModel

    var body: some View {
        List {
            if let verdict = model.result?.correctness?.verdict {
                Section("Engine verdict") {
                    Text(SafetyText.verdictLabel(verdict)).font(.headline)
                }
            }
            if let steps = model.result?.steps, !steps.isEmpty {
                Section("Pipeline") {
                    ForEach(steps) { step in
                        VStack(alignment: .leading) {
                            Text(step.name).font(.subheadline.bold())
                            Text("\(step.status): \(step.detail)")
                                .font(.caption).foregroundStyle(.secondary)
                        }
                    }
                }
            }
            if let caveat = model.result?.caveat {
                Section { Text(caveat).font(.footnote).foregroundStyle(.secondary) }
            }
            Section {
                Button("See progression over time") { model.showProgression() }
            }
        }
    }
}

/// Step 4: staged progression + 3D over time.
struct ProgressionView: View {
    @EnvironmentObject private var model: LiteFlowViewModel

    var body: some View {
        VStack(spacing: 16) {
            if let timeline = model.result?.timeline {
                Text("\(timeline.stageCount) stages")
                    .font(.title3.bold())
                Text("≈ \(timeline.projectedDurationWeeks, specifier: "%.1f") weeks "
                     + "(\(timeline.wearIntervalDays)-day interval)")
                    .font(.subheadline)
                Text(timeline.caveat).font(.caption).foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
            }
            // TODO: SceneKit/Metal 3D preview that animates `plan.stages` movement
            // over time, mirroring ui/viewer3d.js. Mesh bytes come from
            // GET /api/mesh/<id>; fall back to schematic proxy teeth when absent.
            RoundedRectangle(cornerRadius: 12)
                .fill(.gray.opacity(0.12))
                .overlay(Text("3D progression preview\n(TODO: SceneKit renderer)")
                    .multilineTextAlignment(.center).foregroundStyle(.secondary))
                .frame(height: 280)
            Button("Start over") { model.reset() }
        }
        .padding()
        .frame(maxHeight: .infinity)
    }
}
