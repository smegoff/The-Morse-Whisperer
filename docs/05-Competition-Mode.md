# Competition Mode (Known sequence training)

Scenario:
- A known “good” source sends **10 consecutive A characters** ("AAAAAAAAAA").
- Once the decoder reliably matches this sequence, we assume the setup is dialled.

## Recommended workflow
1. Enable Training Mode
2. Select **Manual AAAAAAAAAA** training strategy
3. Start the known sequence
4. When the device confirms **10 consecutive A correct**, it:
   - stops training
   - locks settings (tone/thresholds/dot estimate)
   - continues decoding normally for the competition message

## Why this works
“A” is `.-` which contains both:
- a dot
- a dash
- a letter gap

So it exercises:
- mark timing discrimination
- gap detection
- threshold correctness
- dot estimation stability

This is a robust “sanity test” for contest conditions.
