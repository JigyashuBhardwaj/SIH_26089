import type { Association } from '@shared/types';
import { getAccessToken } from './authService';
import { ApiError, NetworkUnavailableError, request } from './apiClient';

/**
 * Phase 6B-2: the association catalogue now comes from the real backend
 * (`GET /associations`), not a hardcoded local list.
 *
 * The backend models no association-service eligibility relationship at
 * all — `Association` has no link to `Service`, and every demo `Service`
 * currently shares one `category` value, "Home Services" (see
 * `backend/scripts/seed_demo_data.py`), so matching on category would not
 * be a real signal even if attempted. Per this phase's locked scope,
 * every association `GET /associations` returns is therefore treated as
 * selectable — a deliberate MVP simplification, not an oversight. A
 * later phase can add real eligibility once the backend models one.
 *
 * The wire response (`AssociationPublic`, camelCase-aliased) already
 * matches `shared/types/association.ts`'s `Association` interface field
 * for field, so no local type or mapping layer is needed here — unlike
 * `serviceCatalog.ts`, which layers a client-only `icon` field on top.
 */

interface AssociationListResponse {
  items: Association[];
  page: number;
  pageSize: number;
  total: number;
}

/**
 * The largest page size `GET /associations` accepts (backend-enforced,
 * same `PaginationParams.page_size <= 100` cap as `GET /services`).
 */
const MAX_PAGE_SIZE = 100;

/**
 * Fetches every Association row from `GET /associations`. Like
 * `serviceCatalog.ts`'s `fetchServiceCatalog`, this never assumes the
 * whole list fits on one page: it requests the backend's maximum page
 * size and keeps paging — driven by the server-reported `total`, never a
 * hardcoded assumption — until every item has been collected.
 */
export async function fetchAssociationCatalog(): Promise<Association[]> {
  const token = await getAccessToken();
  const collected: Association[] = [];
  let page = 1;

  for (;;) {
    const response = await request<AssociationListResponse>(
      `/associations?page=${page}&page_size=${MAX_PAGE_SIZE}`,
      { token }
    );
    collected.push(...response.items);

    if (response.items.length === 0 || collected.length >= response.total) {
      break;
    }
    page += 1;
  }

  return collected;
}

/**
 * Maps a `fetchAssociationCatalog` failure to a safe, user-facing
 * message — same pattern as `serviceCatalog.ts`'s
 * `describeServiceCatalogError`.
 */
export function describeAssociationCatalogError(err: unknown): string {
  if (err instanceof NetworkUnavailableError) {
    return err.message;
  }
  if (err instanceof ApiError) {
    return err.message;
  }
  return 'Something went wrong while loading associations. Please try again.';
}
