/**
 * A predefined service category/work item a user can book.
 * Users may only select from these — the search field filters this list,
 * it does not accept arbitrary free-text work requests.
 */
export interface Service {
  id: string;
  category: string;
  name: string;
  description?: string;
}
