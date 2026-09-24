import type { ComponentProps } from 'react';
import type { Ionicons } from '@expo/vector-icons';
import type { Service } from '@shared/types';
import { getAccessToken } from './authService';
import { ApiError, NetworkUnavailableError, request } from './apiClient';

/**
 * Phase 6B-1: the service catalogue now comes from the real backend
 * (`GET /services`), not a hardcoded local list. A backend `Service` row
 * has no UI concept of an icon, so `CatalogService` still layers one on
 * top — same shape as before — but the icon is now looked up by the
 * backend's own `name` (a stable, backend-owned property), never used to
 * invent or override the backend `id`. `id`/`category`/`name` on every
 * `CatalogService` this module produces are always exactly what
 * `GET /services` returned; nothing here fabricates or maps a local id to
 * a backend UUID.
 */
export interface CatalogService extends Service {
  icon: ComponentProps<typeof Ionicons>['name'];
}

/**
 * Presentation-only icon lookup, keyed by the backend's `Service.name`.
 * This never gates which services are selectable — a backend service
 * whose name isn't listed here still appears, just with
 * `DEFAULT_SERVICE_ICON`. Names match the current seeded catalogue
 * (`backend/scripts/seed_demo_data.py`'s `SERVICE_CATALOGUE`), but this
 * list is allowed to fall behind that without breaking anything.
 */
const SERVICE_ICON_BY_NAME: Record<string, ComponentProps<typeof Ionicons>['name']> = {
  Plumbing: 'water-outline',
  Electrical: 'flash-outline',
  Carpentry: 'hammer-outline',
  Masonry: 'construct-outline',
  Painting: 'color-palette-outline',
  'Water Heater Technician': 'flame-outline',
  'General Helpers': 'walk-outline',
  Cleaning: 'sparkles-outline',
  Gardening: 'leaf-outline',
};

const DEFAULT_SERVICE_ICON: ComponentProps<typeof Ionicons>['name'] = 'construct-outline';

function iconForServiceName(name: string): ComponentProps<typeof Ionicons>['name'] {
  return SERVICE_ICON_BY_NAME[name] ?? DEFAULT_SERVICE_ICON;
}

/** Raw `GET /services` item shape — camelCase per the backend's Pydantic aliases (`ServicePublic`). */
interface RawService {
  id: string;
  name: string;
  category: string;
  isActive: boolean;
}

interface RawServiceListResponse {
  items: RawService[];
  page: number;
  pageSize: number;
  total: number;
}

function toCatalogService(raw: RawService): CatalogService {
  return {
    id: raw.id,
    name: raw.name,
    category: raw.category,
    icon: iconForServiceName(raw.name),
  };
}

/**
 * The largest page size `GET /services` accepts (backend-enforced:
 * `PaginationParams.page_size` caps at 100). Requesting this explicitly,
 * rather than relying on the endpoint's default page size, is what lets
 * `fetchServiceCatalog` below collect the whole catalogue without
 * assuming any particular total count fits on one page.
 */
const MAX_PAGE_SIZE = 100;

/**
 * Fetches the complete active service catalogue from `GET /services`.
 * The endpoint is paginated and its default page size is not guaranteed
 * to cover every seeded service, so this always requests the backend's
 * maximum page size and keeps requesting subsequent pages — driven by
 * the server-reported `total`, never a hardcoded assumption — until every
 * item has been collected. For the current 9-service demo catalogue this
 * resolves in a single request; it stays correct if that count grows.
 */
export async function fetchServiceCatalog(): Promise<CatalogService[]> {
  const token = await getAccessToken();
  const collected: RawService[] = [];
  let page = 1;

  for (;;) {
    const response = await request<RawServiceListResponse>(
      `/services?page=${page}&page_size=${MAX_PAGE_SIZE}`,
      { token }
    );
    collected.push(...response.items);

    if (response.items.length === 0 || collected.length >= response.total) {
      break;
    }
    page += 1;
  }

  return collected.map(toCatalogService);
}

/**
 * Maps a `fetchServiceCatalog` failure to a safe, user-facing message —
 * shared so every screen that fetches the catalogue reports errors the
 * same way `authService.ts` does for login failures.
 */
export function describeServiceCatalogError(err: unknown): string {
  if (err instanceof NetworkUnavailableError) {
    return err.message;
  }
  if (err instanceof ApiError) {
    return err.message;
  }
  return 'Something went wrong while loading services. Please try again.';
}

/**
 * The catalogue shown by default (empty search). The backend has no
 * "popular" concept of its own, so — unlike the old hardcoded subset —
 * this simply shows every fetched service; with today's 9-item demo
 * catalogue that distinction wasn't meaningful anyway.
 */
export function getPopularServices(catalog: CatalogService[]): CatalogService[] {
  return catalog;
}

/**
 * Filters the fetched catalogue by name/category text. Never returns
 * anything outside `catalog` — there is no path from a typed string to a
 * newly-created or fabricated service.
 */
export function searchServices(catalog: CatalogService[], query: string): CatalogService[] {
  const normalized = query.trim().toLowerCase();
  if (!normalized) {
    return getPopularServices(catalog);
  }
  return catalog.filter(
    (service) =>
      service.name.toLowerCase().includes(normalized) || service.category.toLowerCase().includes(normalized)
  );
}

/**
 * LEGACY, Phase 3A-era static catalogue. Phase 6B-1's own scope is
 * limited to the Book a Service screen (which now uses
 * `fetchServiceCatalog` above exclusively and no longer reads this
 * array), but `select-association.tsx` still imports this constant to
 * resolve the selected service's `category` for association-eligibility
 * matching, and touching that screen is explicitly out of this
 * sub-phase's locked scope. Left byte-for-byte unchanged so that screen
 * keeps compiling and behaving exactly as it did before this patch.
 *
 * Note for whoever picks up the next sub-phase: this array's ids
 * (`'carpenter'`, `'plumbing-helper'`, ...) no longer correspond to any
 * real backend UUID now that Book a Service selects from
 * `fetchServiceCatalog`'s real data — so `select-association.tsx`'s
 * `PREDEFINED_SERVICES.find(service => service.id === serviceId)` lookup
 * will no longer find a match for a service selected via the real Book a
 * Service screen. Separately, the real backend seeds every `Service` row
 * under one shared `category` ("Home Services" — see
 * `backend/scripts/seed_demo_data.py`), so even a corrected lookup would
 * not match any of `associationCatalog.ts`'s per-craft
 * `matchCategories` values. Both of these are flagged, known,
 * out-of-scope consequences of this sub-phase, not something this patch
 * attempts to silently paper over — see the accompanying report.
 */
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
