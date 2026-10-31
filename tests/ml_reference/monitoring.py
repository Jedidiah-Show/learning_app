"""Reference implementation of the Module 4 operations controls."""


class InputShiftMonitor:
    def __init__(self, reference_mean_tickets=1.4, shift_ratio=2.0):
        self.reference_mean_tickets = reference_mean_tickets
        self.shift_ratio = shift_ratio

    def inspect(self, support_ticket_values):
        observed_mean = sum(support_ticket_values) / len(support_ticket_values)
        drifted = observed_mean >= self.reference_mean_tickets * self.shift_ratio
        return {
            'observed_mean': observed_mean,
            'reference_mean': self.reference_mean_tickets,
            'drift_detected': bool(drifted),
            # A shift in inputs is an alert to investigate, never proof that
            # the model stopped performing.
            'model_quality_failed': False,
        }


class CanaryRelease:
    def __init__(self, current_version='1.0.0', error_rate_limit=0.10):
        self.current_version = current_version
        self.error_rate_limit = error_rate_limit

    def evaluate_candidate(self, candidate_version, observed_error_rate):
        promoted = observed_error_rate <= self.error_rate_limit
        return {
            'candidate_version': candidate_version,
            'promoted': bool(promoted),
            'active_version': candidate_version if promoted else self.current_version,
            'rolled_back': bool(not promoted),
        }
