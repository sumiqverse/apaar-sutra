"""Rule implementations package exports."""

from app.validation.rules.r001_to_r004_apaar import (
    RuleR001MissingApaar,
    RuleR002InvalidApaarFormat,
    RuleR003ApaarNotFoundInRegistry,
    RuleR004DemographicMismatch,
)
from app.validation.rules.r010_to_r012_duplicates import (
    RuleR010InternalDuplicate,
    RuleR011CrossInstitutionDuplicate,
    RuleR012ProbableDuplicateWithoutApaar,
)
from app.validation.rules.r020_to_r021_intake import (
    RuleR020IntakeOvershoot,
    RuleR021SupernumeraryCapExceeded,
)
from app.validation.rules.r030_to_r031_consistency import (
    RuleR030InconsistentDemographics,
    RuleR031MissingMandatoryQuotaFields,
)

ALL_RULES = [
    RuleR001MissingApaar,
    RuleR002InvalidApaarFormat,
    RuleR003ApaarNotFoundInRegistry,
    RuleR004DemographicMismatch,
    RuleR010InternalDuplicate,
    RuleR011CrossInstitutionDuplicate,
    RuleR012ProbableDuplicateWithoutApaar,
    RuleR020IntakeOvershoot,
    RuleR021SupernumeraryCapExceeded,
    RuleR030InconsistentDemographics,
    RuleR031MissingMandatoryQuotaFields,
]

__all__ = [
    "RuleR001MissingApaar",
    "RuleR002InvalidApaarFormat",
    "RuleR003ApaarNotFoundInRegistry",
    "RuleR004DemographicMismatch",
    "RuleR010InternalDuplicate",
    "RuleR011CrossInstitutionDuplicate",
    "RuleR012ProbableDuplicateWithoutApaar",
    "RuleR020IntakeOvershoot",
    "RuleR021SupernumeraryCapExceeded",
    "RuleR030InconsistentDemographics",
    "RuleR031MissingMandatoryQuotaFields",
    "ALL_RULES",
]
