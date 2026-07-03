# Field Notes

These notes are intentionally a bit rough. They capture practical assumptions that would usually come from watching a real front desk for a few days.

- The locker number is not the layout. A club should map lockers to physical coordinates before trusting any distance score.
- Lower lockers may be fine for kids, bags, or pool traffic, but many adult gym visitors will prefer upper lockers if they are available.
- The default 10-minute arrival window and 15-minute departure window are guesses. They should be tuned from local observations.
- A staff override should be saved as feedback, not treated as an error. Humans will know about broken doors, groups, and awkward corners first.
- The simulator does not model friends arriving together yet. That probably matters in evening peak hours.
- A real rollout should start as recommendation-only mode before automatic key assignment.

Small TODOs:

- CSV importer for custom locker maps.
- Zone caps for family/kids/pool sections.
- Faster benchmark mode for very large synthetic traffic runs.
- A tiny web dashboard for comparing score weights.
