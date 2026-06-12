import Foundation

/// Standing, non-dismissible safety wording. Kept in sync with the engine
/// `caveat` field and ../../API_CONTRACT.md. The lite app must never present a
/// plan as safe, approved, cleared, or ready for treatment.
public enum SafetyText {
    public static let disclaimer = """
    OpenSource Ortho is a clear-aligner planning safety playground and research \
    toolkit. The current build is not distributed as a medical device, is not \
    complete treatment-planning software, and does not diagnose, treat, approve \
    treatment, or authorize physical use. A CONSISTENT verdict means the staging \
    is internally consistent with the configured caps and controls - not that it \
    is safe, approved, or clinically appropriate. Always consult a licensed \
    dental professional; any physical use is your own responsibility and risk.
    """

    /// Human-facing label for an engine verdict. Verdicts are only ever
    /// "CONSISTENT" or "ISSUES" - never "safe"/"approved".
    public static func verdictLabel(_ verdict: String) -> String {
        switch verdict.uppercased() {
        case "CONSISTENT": return "Internally consistent"
        case "ISSUES":     return "Issues found"
        default:           return verdict
        }
    }
}
