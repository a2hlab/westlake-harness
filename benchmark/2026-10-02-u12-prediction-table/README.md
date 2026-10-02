# U12 prediction table

## Inputs (master, read-only)

- `benchmark/2026-10-02-candidate-first-fatal-clusters/clusters.json`
- `benchmark/2026-10-02-u12-java-walls/predictions.csv`
- `benchmark/2026-10-02-u12-mediandk/predictions.json`
- `benchmark/2026-10-02-u12-icu-zeroinit/results.json`
- `benchmark/2026-10-02-u12-disappeared/predictions.json`
- `benchmark/2026-10-02-u12-sigabrt/results.json`
- `benchmark/2026-10-02-n11h-predictions/n11h-predictions.csv`

## Counts

- rows: 51
- java_fix: 13/13
- java_moves: 13/13
- mediandk: 2/2
- icu: 2/2
- disappeared: 6/6
- sigabrt: 8/8
- n11h: 14/18
- owners >= 2: 2
- any_predicted_mover: 22

## Owners >= 2 (conflict keys)

- `cv2-com-chessclock-android`: owners=2, java_fix=-, mediandk=media_jni absent from trusted adapter manifest; MediaPlayer., icu=, disappeared=, sigabrt=, n11h=
- `subwaysurfers`: owners=2, java_fix=, mediandk=libmain FatalError after libunity NEEDED libmediandk.so fail, icu=, disappeared=, sigabrt=unity-required-media-provider | libmain native loader FatalE, n11h=
