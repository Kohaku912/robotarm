# サーボCADデータ反映状況

## 取り込んだユーザーデータ

| ファイル | SHA/保存先 | 使用内容 |
|---|---|---|
| MG90s_Horn.step | `vendor/servo_cad/MG90S_HORN.step` | 36×8×5 mmのダブルアームホーン。J1/J4/J5に使用 |
| MG90S Micro Servo Motor.step | `vendor/servo_cad/MG90S_SERVO.step` | 中央保持ねじ形状とホーン組付け基準 |
| Servo MG996R.STEP | `vendor/servo_cad/MG996R_SERVO.step` | MG996R筐体・出力スプライン参照。ホーンは含まれない |

SHA-256: MG90S horn `8C428DD318A7E22E306891E47F606A9B6688F3669DC7F9C54D71B26543957D99`; MG90S servo `655BE9FACE0FC062FCAF81FB7811722D9DA1611A2E4B36BA4494F5C3845A1293`; MG996R servo `6FABFCE4C057604B33F8E49768FB1886B1E99FB4CBFA6001B8DBA6BCD5FC6E18`.

MG90S実ホーンの取付穴列は中心から左右6.5、9.0、11.5、14.0、16.5 mm。V8では最内側の±6.5 mmを使用する。J1はM2×7とM2 OD3.5×L3熱圧入インサート、J4はM3×15とM3 OD6×L4インサート、J5はM2×5とロックナットで締結する。すべてにサーボ付属中央保持ねじを独立部品として追加した。

J1ではホーンを37.5°回して惑星歯車と締結部品を離した。J4/J5ではホーン腕を縦向きにし、隣接サーボ・側板との干渉を回避した。J5ハウジングには実ホーン腕用スロットを追加した。

MG996Rデータは単一ソリッドでホーンを含まない。このためJ2/J3のホーンと受け座は最終形状ではなく、監査 `AUD-EXACT-SERVO-HORN-GEOMETRY` を意図的にFAILとする。

## サーボ本体の実STEP置換（2026-08-06）

- J1/J4/J5の本体は `MG90S_SERVO.step` の筐体＋出力軸ソリッドを無加工で配置した。出力基準はローカル `(0,0,0)`、軸はローカルZ。取付穴は直径2.4 mm、ローカルX=`-8.55, 19.15 mm`、穴厚2.4 mm。
- J2/J3の本体は `MG996R_SERVO.step` の単一ソリッドを無加工で配置した。出力基準はローカル `(10,47.6,-10) mm`、軸はローカルY。取付スロットは直径4.44 mm、X=`-5.0,45.3 mm`、Z=`-5.5,-14.5 mm`。
- `AUD-EXACT-SERVO-BODY-GEOMETRY` は5台すべてのSTEP出典を検査し、`AUD-PURCHASED-SERVO-UNMODIFIED` は配置後B-rep体積と元STEP体積を0.01 mm³以内で比較する。両方PASS。
- J2/J3は実スロットへM4低頭ねじ4本とM4 OD5×L4熱圧入インサートで固定する。J1/J4/J5は実2.4 mm穴へM2×8ねじとM2 OD3.5×L3インサートで固定する。購入サーボには切削、穴拡大、ボス追加を行わない。
- 実MG90S同士が旧J4–J5軸間30 mmで1,169.037 mm³干渉したため、J5軸をX=273 mmへ13 mm移動した。現在のケース間最小X余裕は約4.7 mm。
