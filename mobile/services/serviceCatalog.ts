import type { ComponentProps } from 'react';
import type { Ionicons } from '@expo/vector-icons';
import type { Service } from '@shared/types';

/**
 * Predefined service catalogue for this prototype.
 *
 * This is intentionally local to the mobile app, not `shared/`: the
 * catalogue's *shape* (`Service`) is a shared domain type, but this
 * specific mock list plus its UI icon mapping is prototype data that will
 * be replaced by a real "GET /services" backend call in a later phase —
 * exactly the same pattern `authService.ts` uses for mock auth. Keeping
 * the icon field here (not in `shared/types/service.ts`) also keeps the
 * shared layer framework-agnostic — it has no reason to know about
 * `@expo/vector-icons`.
 *
 * The user can only ever select one of these entries. Typing in the
 * search box filters this list — it never creates a new, arbitrary
 * service.
 */
export interface CatalogService extends Service {
  icon: ComponentProps<typeof Ionicons>['name'];
}

export const PREDEFINED_SERVICES: CatalogService[] = [
  {
    id: 'carpenter',
    category: 'Carpentry',
    name: 'Carpenter',
    description: 'Furniture repair, woodwork, fittings, and custom carpentry.',
    icon: 'hammer-outline',
  },
  {
    id: 'electrician',
    category: 'Electrical',
    name: 'Electrician',
    description: 'Wiring, switchboards, appliance repair, and installations.',
    icon: 'flash-outline',
  },
  {
    id: 'plumber',
    category: 'Plumbing',
    name: 'Plumber',
    description: 'Pipe repair, installation, leakage fixing, bathroom fittings, etc.',
    icon: 'water-outline',
  },
  {
    id: 'plumbing-helper',
    category: 'Plumbing',
    name: 'Plumbing Helper',
    description: 'Assistance with plumbing work.',
    icon: 'build-outline',
  },
  {
    id: 'water-heater-technician',
    category: 'Plumbing',
    name: 'Water Heater Technician',
    description: 'Installation and repair of geysers and water heaters.',
    icon: 'flame-outline',
  },
  {
    id: 'mason',
    category: 'Masonry',
    name: 'Mason',
    description: 'Brickwork, plastering, tiling, and construction support.',
    icon: 'construct-outline',
  },
  {
    id: 'painter',
    category: 'Painting',
    name: 'Painter',
    description: 'Interior and exterior painting, wall finishing.',
    icon: 'color-palette-outline',
  },
  {
    id: 'helper',
    category: 'General',
    name: 'Helper',
    description: 'General labour support for daily household or site tasks.',
    icon: 'walk-outline',
  },
  {
    id: 'driver',
    category: 'Transport',
    name: 'Driver',
    description: 'Local transport, deliveries, and errands.',
    icon: 'car-outline',
  },
  {
    id: 'gardener',
    category: 'Gardening',
    name: 'Gardener',
    description: 'Lawn care, planting, and garden maintenance.',
    icon: 'leaf-outline',
  },
  {
    id: 'cleaner',
    category: 'Cleaning',
    name: 'Cleaner',
    description: 'Home and office cleaning services.',
    icon: 'sparkles-outline',
  },
];

/** The subset shown by default (empty search) — mirrors the reference's "Popular Services" grid. */
export const POPULAR_SERVICE_IDS = [
  'carpenter',
  'electrician',
  'plumber',
  'mason',
  'painter',
  'helper',
  'driver',
  'gardener',
  'cleaner',
];

export function getPopularServices(): CatalogService[] {
  return PREDEFINED_SERVICES.filter((service) => POPULAR_SERVICE_IDS.includes(service.id));
}

/**
 * Filters the predefined catalogue by name/category text. Never returns
 * anything outside `PREDEFINED_SERVICES` — there is no path from a typed
 * string to a newly-created service.
 */
export function searchServices(query: string): CatalogService[] {
  const normalized = query.trim().toLowerCase();
  if (!normalized) {
    return getPopularServices();
  }
  return PREDEFINED_SERVICES.filter(
    (service) =>
      service.name.toLowerCase().includes(normalized) || service.category.toLowerCase().includes(normalized)
  );
}
