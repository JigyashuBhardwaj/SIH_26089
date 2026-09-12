import type { CatalogService } from './serviceCatalog';

/**
 * Demo labour associations for this prototype. Local to the mobile app,
 * same reasoning as `serviceCatalog.ts`: this specific data will be
 * replaced by a real association directory call in a later phase, but
 * the shape stays the same so screens don't need to change.
 *
 * These are demo/prototype associations only — no real-world affiliation
 * is implied.
 */
export interface Association {
  id: string;
  name: string;
  /**
   * Exact category strings from the Phase 3A service catalogue
   * (`shared`/`CatalogService.category`) that this association supports.
   * Used for eligibility matching — must line up with
   * `mobile/services/serviceCatalog.ts` categories.
   */
  matchCategories: string[];
  /** Human-readable service list shown on the card (can read more naturally than matchCategories). */
  displayServices: string[];
  rating: number;
  /** Pre-formatted worker count, e.g. "120+". */
  workerCount: string;
}

export const ASSOCIATIONS: Association[] = [
  {
    id: 'dhanbad-skilled-workers',
    name: 'Dhanbad Skilled Workers Association',
    matchCategories: ['Plumbing', 'Electrical', 'Carpentry', 'Masonry'],
    displayServices: ['Plumbing', 'Electrical', 'Carpentry', 'Masonry'],
    rating: 4.7,
    workerCount: '120+',
  },
  {
    id: 'dhanbad-general-workers',
    name: 'Dhanbad General Workers Association',
    // "General" matches the Phase 3A "Helper" service's category; the
    // card itself displays the friendlier "General Helpers" label below.
    matchCategories: ['Plumbing', 'Painting', 'Cleaning', 'Gardening', 'General'],
    displayServices: ['Plumbing', 'Painting', 'Cleaning', 'Gardening', 'General Helpers'],
    rating: 4.5,
    workerCount: '95+',
  },
];

/**
 * Associations eligible for a given Phase 3A service. Matches on the
 * service's `category` (from the authoritative Phase 3A catalogue), not
 * on free text, so eligibility always stays in sync with what services
 * actually exist.
 */
export function getEligibleAssociations(service: Pick<CatalogService, 'category'>): Association[] {
  return ASSOCIATIONS.filter((association) => association.matchCategories.includes(service.category));
}
