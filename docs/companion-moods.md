# Companion moods

Mica and Tuck keep their original animated GIFs. The five newer moods add shake, tilt, bounce, sway or pop motion around the corresponding original activity. There is no manual mood picker and no claim of five newly drawn facial GIFs.

| Mood | Trigger | Original animation |
| --- | --- | --- |
| Curious | Learning or waiting for a game answer | Thinking |
| Happy | A successful task/routine | Done |
| Angry | A failed task/routine | Stuck |
| Sleepy | Quiet idle through the phone activity timer | Idle |
| Surprised | A new step-away prompt | Needs-you |

Approvals keep the needs-you activity. Brief reactions return to the current flow; old completed tasks do not replay. Active moods refresh before the desktop lease expires. Phone reduced-motion mode uses still artwork; native motion layers respect their platform’s animation settings.

Tests cover automatic state transitions, actual multi-frame GIF assets, original-GIF selection, relay validation and mood refresh. Native builds compile, and Windows CI checks its worker and companion build. Physical devices are still needed to verify every visual reaction in context.
