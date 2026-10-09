# bindings-v1

Retained local display associations, carried as the bounded `localBindings`
extension on the local host in Fleet v1. See
`docs/local-performance-implementation.md` for scope and acceptance.

`open` means a current native tmux client has a previously resolved unique Kitty
association in this desktop context. `resolvedAt` is the original discovery
time, which need not be within the current native lease. It never means freshly
captured desktop presence. A consumer may show qualified Open membership; it
must not convert this to C3 confirmation or action authority. `none` means zero
current native clients, not a complete fresh scan of desktop windows. Other
cases remain `unknown` with a reason.

The ready receipt is prepared from complete current native inputs. Its expiry
is bounded independently by the owner and local client-association receipts.
Encoding, cached delivery and heartbeats renew neither dependency. Discovery
time never changes solely because a native receipt renewed. Scope, complete
reference coverage and native attachment counts must agree with the enclosing
local Fleet host. A failed or expired dependency revokes positives.

No client/window PID, window ID, terminal contents or action handles are
published. Kitty tab/window relocation that preserves a client can leave a
retained association outdated; explicit refresh can rediscover it. Actions
resolve and validate their targets separately. The bundle and all identities
in its fixtures are synthetic and establish no runtime acceptance.
