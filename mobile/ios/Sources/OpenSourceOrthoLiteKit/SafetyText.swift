import Foundation

/// Standing, non-dismissible safety wording. Kept in sync with the engine
/// `caveat` field and ../../API_CONTRACT.md. The lite app must never present a
/// plan as safe, approved, cleared, or ready for treatment.
public enum SafetyText {
    public static let disclaimer = """
    OpenSource Ortho is an educational and research toolkit. It is not a medical \
    device and does not diagnose, treat, or approve treatment. A CONSISTENT \
    verdict means the staging is internally consistent with the configured caps \
    and controls - not that it is safe, approved, or clinically appropriate. \
    Always consult a licensed dental professional.
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
