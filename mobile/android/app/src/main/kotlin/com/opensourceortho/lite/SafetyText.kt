package com.opensourceortho.lite

/**
 * Verdict labelling. The standing disclaimer text itself lives in
 * res/values/strings.xml (`safety_disclaimer`) so it is localizable; this object
 * only maps engine verdicts to human labels. Verdicts are only ever "CONSISTENT"
 * or "ISSUES" - never "safe"/"approved".
 */
object SafetyText {
    fun verdictLabel(verdict: String): String = when (verdict.uppercase()) {
        "CONSISTENT" -> "Internally consistent"
        "ISSUES" -> "Issues found"
        else -> verdict
    }
}
