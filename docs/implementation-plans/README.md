# Implementation Plans

このディレクトリには、各Issueの実装計画書を格納します。

## 命名規則

`IMPLEMENTATION_PLAN_ISSUE{番号}.md`

例: `IMPLEMENTATION_PLAN_ISSUE25.md`

## 実装計画書の内容

各実装計画書には以下の情報を含めます:

- **Issue番号とブランチ名**
- **実装方針**: 基本原則とアーキテクチャ
- **Phase別の実装ステップ**: 各ステップの所要時間と成功基準
- **成功基準**: 各Phaseの完了条件
- **中断判断**: エラー発生時の対応
- **最終確認チェックリスト**

## 既存の実装計画

- [Issue #25: Mermaid図解統合](./IMPLEMENTATION_PLAN_ISSUE25.md)
- [スライド履歴プレビュー機能 + user_id問題修正](./IMPLEMENTATION_PLAN_HISTORY_PREVIEW.md)
- [Supabase Storage移行計画](./SUPABASE_STORAGE_MIGRATION.md) - Cloud Run対応のための永続化
- [デプロイ計画（Firebase Hosting + Cloud Run）](./DEPLOYMENT_PLAN_FIREBASE_CLOUDRUN.md) - 本番環境デプロイ手順
