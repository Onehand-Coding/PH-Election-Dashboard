## Election Data Format

This directory contains sample data files for the Philippine Election Dashboard.

### Common Columns
- `Position`: The position being contested (e.g., Senator, Governor, Barangay Captain).
- `Candidate_Name`: The name of the candidate.
- `Party`: The political party of the candidate. Can be 'Independent' or blank if not applicable.
- `Total_Votes`: The total number of votes received by the candidate.

### `national_election_results.csv`
- `Position`: Senator, Party-List.
- `Region_Focus`: Typically "National" for these positions. (Can be adapted if specific regional focus for senators is tracked).

### `local_election_results.csv`
- `Region`: The administrative region (e.g., NCR, Region III).
- `Province`: The province.
- `Municipality_City`: The municipality or city. This will be blank for provincial-level positions like Governor.

### `barangay_election_results.csv`
- `Region`: The administrative region.
- `Province`: The province.
- `Municipality_City`: The municipality or city.
- `Barangay`: The barangay.

Ensure CSV files are comma-delimited and UTF-8 encoded.
