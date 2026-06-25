-- Let Supabase's PostgREST login role (authenticator) SET ROLE into chat_remote,
-- so a request with a JWT role claim of 'chat_remote' is served with exactly
-- chat_remote's privileges. Only load-bearing for the PostgREST data-API route
-- (Option B); harmless under the Supabase-MCP route (Option A).
grant chat_remote to authenticator;
