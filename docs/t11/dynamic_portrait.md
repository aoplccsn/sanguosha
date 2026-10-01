# T11 god portrait runtime checkpoint

The Web client now has a shared `GodPortrait` component and a Lu Bu prototype wired to player panels and general details. High and Medium render a moving battlefield plate plus alpha-enabled character plate; High adds a lightweight ember layer. Low uses the static source portrait. CSS transform and opacity handle idle breathing, entry, attack, hit and victory cues; dying darkens the composition. Reduced-motion disables repeating motion.

The prototype is intentionally incomplete. The character cutout has environmental color around some edges; the face, eyes, hair, cape, weapon and foreground are not separate assets. Blink, independent cloth/hair motion and genuine skill cinematics are not implemented. Because god skill logic remains disabled, this does not open Lu Bu or any other god for normal play. Attack cues use only public event semantics and do not modify rule outcomes.

Next art pass: clean the body cutout, generate/paint isolated face/eye, hair, cloth and weapon layers, then replace the CSS prototype with a layer manifest consumed by the shared portrait runtime. Validate visual registration at portrait and detail sizes before enabling a character.
