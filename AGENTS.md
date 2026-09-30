# Agent instructions

## 実装・検証・レビューの運用

通常実装は一人のprimary agentが、調査・設計・実装・変更に必要な検証・失敗の修正・文書同期まで一貫して担当する。repository側では特定modelやmodel間の担当分担を固定せず、model選択はsystem / developer instruction、Codexのユーザー設定・実効設定、ユーザーの明示指定に従う。独立レビューは重要な設計判断、高リスク変更、明示gateなど実質的な独立性が必要な場合にだけ追加する。

有効な同条件の検証は再利用し、不完全レビューは不足部分を補完する。環境障害は失敗箇所から再開する。全面実操作E2Eはリリース前の統合段階、変更に必要な検証はその場で行う。関連Skillから古い担当指定・追加の全面再実行義務を持ち込まない。条件・独立性・権限境界の正本は[実行ワークフロー](docs/agent-workflow.md)。

対象Issue / PRとREADME、関連する実装・testsを確認する。未確認の仕様・データを創作せず、既存ユーザー変更を保護する。mainへ直接pushせず、feature branchとDraft PRを使う。merge、公開、破壊的操作には明示許可を必要とする。
