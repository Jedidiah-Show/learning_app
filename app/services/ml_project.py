"""Shared ML project submission labels and workflow rules."""

FAILURE_STAGES = {
    'report_contract': 'Report does not match the fixed dataset contract',
    'ci_verification': 'Public automated checks could not be verified',
    'review_unavailable': 'Automated review unavailable (submission saved)',
    'review_invalid': 'Automated review returned an invalid result',
    'rubric_below_threshold': 'Review completed but below the pass threshold',
}
