# Load a benchmark case by id

load_case(cases, case_id) must return the first manifest object whose id exactly matches case_id. Raise KeyError with the missing id in the message when there is no match. Do not mutate cases.
