# FreeCAD 6軸カメラグリッパアーム（現実的再設計）

OmArm / Omartronics 系の実機パターン（**サーボ片側＋対向フランジ軸受＋ホーン締結**）に合わせ、**2Dスケッチ→押し出し**で部品を生成します。物理演算は **URDF + PyBullet**（推奨）または **numpy フォールバック**です。

## 仕様まとめ

| 項目 | 値 |
|------|-----|
| 到達距離（目安） | ~350 mm（上腕140 + 前腕120 + 手首~70） |
| ペイロード | 先端 100 g |
| サーボ | MG996R×2（J1/J2）、MG90S×6（J3–J6・グリッパ・カメラチルト） |
| 軸受 | F695ZZ×5、F685ZZ×5 |
| 印刷 | 1パーツ ≤180 mm |

詳細根拠: [`docs/design_notes.md`](docs/design_notes.md)  
2D図面: [`docs/2d/`](docs/2d/)

## 生成（FreeCAD）

```python
exec(open(r"C:/Users/kohak/programs/robotarm/generate_arm.py", encoding="utf-8").read())
```

出力:

- `export/stl/` … 印刷用 STL（20点）
- `export/fcstd/RobotArm.FCStd` … アセンブリ
- `export/vendor/*.step` … サーボ／軸受／ホーン参照
- `urdf/robot_arm.urdf` + `urdf/meshes/`
- `docs/2d/*.svg` … 2Dプロファイル

SVGのみ再出力: `python cad/export_svg.py`

## 検証

```bash
py -3.11 tests/run_validation.py
```

結果: `export/validation_report.json`（print_size / fastener / fk_reach / collision / servo_drive / self_collision）

締結は**接着禁止**（ねじ・圧入・軸嵌合のみ）。詳細は [`bom.md`](bom.md)。

## 物理シミュレーション

### PyBullet GUI（操作デモ）

Python **3.10–3.12** が必要です。

```bash
py -3.11 -m pip install pybullet
py -3.11 sim/pybullet_arm.py
```

または `sim/run_gui.bat`。スライダーで j1–j6・グリッパ・カメラチルトを動かすと、重力下でアーム全体が追従します。

GUI スライダーで各サーボ角を変えると、重力下でアーム全体が追従します。ヘッドレス確認:

```bash
py -3.11 sim/pybullet_arm.py --direct
```

### numpy フォールバック

PyBullet が使えない環境向け。PDサーボ追従＋重力トルクの簡易物理:

```bash
py -3.11 -m pip install numpy matplotlib
py -3.11 sim/numpy_physics_arm.py
# または
py -3.11 sim/numpy_physics_arm.py --no-plot
```

## 関節構造（統一）

1. 固定側: サーボポケット（公開寸法のタブ穴）
2. 駆動側: 円形ホーンをリンクにねじ止め
3. 反対側: F695/F685 フランジ軸受座 + Ø5 軸
4. ケーブル通し穴、分割リンクはダボ + M3 インサート

## 組立順（概略）

1. ベース板＋カラムに MG996R と F695ZZ → タレット下面軸受・ホーン結合  
2. タレット U 頬に F695ZZ×2 → 肩 MG996R → ホーン／アイドラを上腕へ  
3. 上腕分割結合 → 肘 MG90S + F695ZZ  
4. 前腕 → 手首ピッチ／ロール／ヨー（F685ZZ）  
5. グリッパ → カメラチルト（60×8 基板、Ø6 レンズ逃げ）

締結詳細は [`bom.md`](bom.md)。

## 寸法変更

[`params.py`](params.py) を編集して FreeCAD で再生成してください。
