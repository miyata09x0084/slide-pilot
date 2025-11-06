/**
 * types/の型定義テスト
 * Phase 1で抽出した型定義が正しくエクスポートされているか確認
 */

import { describe, it, expect } from 'vitest';
import type { Slide, SlideHistory, User } from '../index';

describe('Type definitions', () => {
  describe('Slide type', () => {
    it('should accept valid Slide object', () => {
      const slide: Slide = {
        id: 'test-id',
        title: 'Test Slide',
        created_at: '2025-11-06T00:00:00Z',
      };
      expect(slide.id).toBe('test-id');
      expect(slide.title).toBe('Test Slide');
    });

    it('should accept Slide with optional fields', () => {
      const slide: Slide = {
        id: 'test-id',
        title: 'Test Slide',
        created_at: '2025-11-06T00:00:00Z',
        file_path: '/path/to/slide.md',
        markdown: '# Test Content',
      };
      expect(slide.file_path).toBe('/path/to/slide.md');
      expect(slide.markdown).toBe('# Test Content');
    });
  });

  describe('SlideHistory type', () => {
    it('should accept valid SlideHistory object', () => {
      const history: SlideHistory = {
        slides: [
          {
            id: '1',
            title: 'Slide 1',
            created_at: '2025-11-06T00:00:00Z',
          },
          {
            id: '2',
            title: 'Slide 2',
            created_at: '2025-11-06T01:00:00Z',
          },
        ],
      };
      expect(history.slides).toHaveLength(2);
      expect(history.slides[0].id).toBe('1');
    });
  });

  describe('User type', () => {
    it('should accept valid User object', () => {
      const user: User = {
        name: 'Test User',
        email: 'test@example.com',
        picture: 'https://example.com/avatar.jpg',
      };
      expect(user.name).toBe('Test User');
      expect(user.email).toBe('test@example.com');
      expect(user.picture).toBe('https://example.com/avatar.jpg');
    });
  });
});
