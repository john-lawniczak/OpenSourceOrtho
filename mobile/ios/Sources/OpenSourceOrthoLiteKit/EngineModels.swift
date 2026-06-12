import Foundation

/// Codable mirrors of the mobile-facing subset of the engine contract
/// (../../API_CONTRACT.md). Only the fields the lite UI renders are modeled;
/// unknown fields are ignored so the engine can evolve without breaking decode.

/// Request body for `POST /api/generate-plan`. Lite defaults keep everything on
/// the engine host: `provider = "local"`, `shareAcknowledged = false`.
public struct GeneratePlanRequest: Codable, Sendable {
    public var plan: [String: AnyCodable]
    public var acknowledgeEducational: Bool
    public var provider: String
    public var shareAcknowledged: Bool
    public var notes: String?

    public init(
        plan: [String: AnyCodable],
        acknowledgeEducational: Bool = true,
        provider: String = "local",
        shareAcknowledged: Bool = false,
        notes: String? = nil
    ) {
        self.plan = plan
        self.acknowledgeEducational = acknowledgeEducational
        self.provider = provider
        self.shareAcknowledged = shareAcknowledged
        self.notes = notes
    }

    enum CodingKeys: String, CodingKey {
        case plan
        case acknowledgeEducational = "acknowledge_educational"
        case provider
        case shareAcknowledged = "share_acknowledged"
        case notes
    }
}

public struct PipelineStep: Codable, Sendable, Identifiable {
    public var name: String
    public var status: String
    public var detail: String
    public var id: String { name }

    public init(name: String, status: String = "ok", detail: String = "") {
        self.name = name
        self.status = status
        self.detail = detail
    }
}

public struct Correctness: Codable, Sendable {
    public var verdict: String
    public init(verdict: String) { self.verdict = verdict }
}

public struct Timeline: Codable, Sendable {
    public var stageCount: Int
    public var wearIntervalDays: Int
    public var projectedDurationDays: Int
    public var projectedDurationWeeks: Double
    public var caveat: String

    public init(
        stageCount: Int,
        wearIntervalDays: Int,
        projectedDurationDays: Int,
        projectedDurationWeeks: Double,
        caveat: String
    ) {
        self.stageCount = stageCount
        self.wearIntervalDays = wearIntervalDays
        self.projectedDurationDays = projectedDurationDays
        self.projectedDurationWeeks = projectedDurationWeeks
        self.caveat = caveat
    }

    enum CodingKeys: String, CodingKey {
        case stageCount = "stage_count"
        case wearIntervalDays = "wear_interval_days"
        case projectedDurationDays = "projected_duration_days"
        case projectedDurationWeeks = "projected_duration_weeks"
        case caveat
    }
}

/// Subset of the `POST /api/generate-plan` success body the lite UI renders.
public struct GeneratePlanResponse: Codable, Sendable {
    public var ok: Bool
    public var errors: [String]?
    public var source: String?
    public var warnings: [String]?
    public var steps: [PipelineStep]?
    public var correctness: Correctness?
    public var stageCount: Int?
    public var timeline: Timeline?
    public var caveat: String?
    /// The full generated plan; stages drive progression rendering. Kept opaque
    /// here - the progression view reads `plan.stages` lazily.
    public var plan: AnyCodable?

    public init(
        ok: Bool = false,
        errors: [String]? = nil,
        source: String? = nil,
        warnings: [String]? = nil,
        steps: [PipelineStep]? = nil,
        correctness: Correctness? = nil,
        stageCount: Int? = nil,
        timeline: Timeline? = nil,
        caveat: String? = nil,
        plan: AnyCodable? = nil
    ) {
        self.ok = ok
        self.errors = errors
        self.source = source
        self.warnings = warnings
        self.steps = steps
        self.correctness = correctness
        self.stageCount = stageCount
        self.timeline = timeline
        self.caveat = caveat
        self.plan = plan
    }

    enum CodingKeys: String, CodingKey {
        case ok, errors, source, warnings, steps, correctness, timeline, caveat, plan
        case stageCount = "stage_count"
    }
}

public struct StoredCaseReview: Codable, Sendable, Equatable {
    public var schema: String
    public var kind: String
    public var caseId: String
    public var planId: String
    public var title: String
    public var reviewTier: ReviewTierSummary
    public var unresolvedDataGaps: [ReviewDataGap]
    public var cbctStatus: String
    public var rootBoneReview: RootBoneReviewSummary
    public var findingsSummary: FindingsSummary
    public var editable: EditLockSummary
    public var handoff: CaseHandoffSummary
    public var planSha256: String
    public var reviewSha256: String

    public var isImportableStoredReview: Bool {
        schema == "orthoplan-case-review-v1" &&
            kind == "stored-review" &&
            editable.inMobile == false &&
            editable.requiresBrowserEngine
    }

    public var mobileSummary: String {
        "\(reviewTier.label) - \(unresolvedDataGaps.count) unresolved data gaps"
    }

    enum CodingKeys: String, CodingKey {
        case schema, kind, title
        case caseId = "case_id"
        case planId = "plan_id"
        case reviewTier = "review_tier"
        case unresolvedDataGaps = "unresolved_data_gaps"
        case cbctStatus = "cbct_status"
        case rootBoneReview = "root_bone_review"
        case findingsSummary = "findings_summary"
        case editable, handoff
        case planSha256 = "plan_sha256"
        case reviewSha256 = "review_sha256"
    }
}

public struct ReviewTierSummary: Codable, Sendable, Equatable {
    public var tier: String
    public var rank: Int
    public var label: String
    public var summary: String
    public var rootBoneAware: Bool

    enum CodingKeys: String, CodingKey {
        case tier, rank, label, summary
        case rootBoneAware = "root_bone_aware"
    }
}

public struct ReviewDataGap: Codable, Sendable, Equatable, Identifiable {
    public var domain: String
    public var reason: String
    public var id: String { domain }
}

public struct RootBoneReviewSummary: Codable, Sendable, Equatable {
    public var verdict: String
}

public struct FindingsSummary: Codable, Sendable, Equatable {
    public var total: Int
    public var bySeverity: [String: Int]

    enum CodingKeys: String, CodingKey {
        case total
        case bySeverity = "by_severity"
    }
}

public struct EditLockSummary: Codable, Sendable, Equatable {
    public var inMobile: Bool
    public var requiresBrowserEngine: Bool
    public var reason: String

    enum CodingKeys: String, CodingKey {
        case reason
        case inMobile = "in_mobile"
        case requiresBrowserEngine = "requires_browser_engine"
    }
}

public struct CaseHandoffSummary: Codable, Sendable, Equatable {
    public var caseId: String
    public var openUrl: String?
    public var deepLink: String
    public var qrPayload: String

    public var openURL: URL? {
        guard let openUrl else { return nil }
        return URL(string: openUrl)
    }

    public var deepLinkURL: URL? {
        URL(string: deepLink)
    }

    enum CodingKeys: String, CodingKey {
        case caseId = "case_id"
        case openUrl = "open_url"
        case deepLink = "deep_link"
        case qrPayload = "qr_payload"
    }
}
