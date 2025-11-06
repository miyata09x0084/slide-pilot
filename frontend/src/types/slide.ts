export interface Slide {
  id: string;
  title: string;
  created_at: string;
  file_path?: string;
  markdown?: string;
}

export interface SlideHistory {
  slides: Slide[];
}
