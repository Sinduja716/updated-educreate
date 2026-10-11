export type WorkflowStage = 'STAGE_1_PROMPT' | 'STAGE_2_OPTIONS' | 'STAGE_3_WORKSPACE';
export type ViewState = 'CREATE' | 'HISTORY' | 'LIBRARY' | 'USAGE' | 'SETTINGS';

export type OutputCategory = 'Posters' | 'Flashcards' | 'Worksheets' | 'Images';

export type AgeGroup = '3-5' | '6-8' | '9-11' | '12-14' | '15-18';

export type Tier = 'draft' | 'standard' | 'high';
export type ColourMode = 'outline' | 'colour';

export type ImageStatus = 'Ready' | 'Checking' | 'Found' | 'Generating' | 'Completed' | 'Failed' | 'Error';

export interface ImageResult {
  id: string;
  url?: string;
  status: ImageStatus;
  isRetrieved: boolean;
  errorMessage?: string;
  tier?: Tier;
  neurons?: number;
}

export interface CreationSession {
  id: string;
  title: string;
  timestamp: string;
  prompt: string;
  category?: OutputCategory;
  ageGroup?: AgeGroup;
  quantity?: number;
  images: ImageResult[];
  metrics?: SessionMetrics;
  planId?: string;
  material?: string;
  tier?: Tier;
  colourMode?: ColourMode;
}

export interface SessionMetrics {
  requested: number;
  reused: number;
  generated: number;
  resourceUsage: string;
  estimatedCost: string;
  savings: string;
  neuronsUsed?: number;
  baselineNeurons?: number;
  savingPercent?: number | null;
  secondsUsed?: number | null;
  timeSavingPercent?: number | null;
  tier?: Tier;
}

export interface GlobalMetrics {
  totalRequested: number;
  totalGenerated: number;
  totalReused: number;
  totalResourceUsage: string;
  totalCost: string;
  totalResourceSaved: string;
  totalCostSaved: string;
  savingsPercentage: string;
}

export interface UserPreferences {
  theme: 'Light' | 'Dark' | 'System';
  density: 'Compact' | 'Comfortable';
  defaultCategory?: OutputCategory;
  defaultOrientation: 'Portrait' | 'Landscape' | 'Square';
  defaultQuantity: number;
  showCostEstimates: boolean;
  defaultDownloadFormat: 'PNG' | 'PDF';
  defaultExportSize: 'A4' | 'A3' | 'Letter';
}
