/**
 * A cooperative labour association (or federation) that verifies workers
 * and operates the Admin Dashboard.
 *
 * Phase 6A: corrected to match the actual backend `AssociationPublic`
 * response (`backend/app/schemas/association.py`) exactly — this
 * interface previously had a `pinCodesServed: string[]` field that does
 * not exist on the real backend `Association` model (only `id`,
 * `federation_id`, `name` are modeled; pincode coverage is explicitly
 * not modeled at all, per that model's own docstring) and an optional
 * `federationId?`, when the backend's `federation_id` is always present.
 * Nothing in `mobile/` or `admin/` consumed this interface at the time
 * of this correction, so this is a type-only change with no behavior
 * impact.
 */
export interface Association {
  id: string;
  federationId: string;
  name: string;
  createdAt: string;
  updatedAt: string;
}
