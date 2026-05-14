[33mcommit 504d770652c9db54dc96ba5e0b1ce4a6bfbce5c3[m[33m ([m[1;36mHEAD[m[33m -> [m[1;32mChandana_Code_Base[m[33m)[m
Author: admin@affine <38282567+adminaffine@users.noreply.github.com>
Date:   Thu May 14 17:40:39 2026 +0530

    MongoDB Community Edition metadata-store migration
    
    - Added Cosmos-API-compatible MongoDB adapter (utility/mongo_document_store.py).
    - METADATA_BACKEND=mongo|cosmos env flag in unified.env for one-flip rollback.
      (env file gitignored; new vars need to be added manually on each machine.)
    - One-shot data-migration script (scripts/migrate_cosmos_to_mongo.py).
    - Rewrote the single Cosmos-only SELECT DISTINCT call site for portable
      cross-backend semantics.
    - All routers/services unchanged; same container API surface works on both
      backends via the adapter.

 Backend/main.py                            |  29 [32m+[m[31m-[m
 Backend/requirements1.txt                  | Bin [31m10038[m -> [32m10070[m bytes
 Backend/routers/userManagementRouter.py    |  18 [32m+[m[31m-[m
 Backend/scripts/migrate_cosmos_to_mongo.py | 211 [32m++++++++++[m
 Backend/services/setupService.py           |  54 [32m++[m[31m-[m
 Backend/utility/helper.py                  |  51 [32m++[m[31m-[m
 Backend/utility/main.py                    |  30 [32m+[m[31m-[m
 Backend/utility/mongo_document_store.py    | 597 [32m+++++++++++++++++++++++++++++[m
 8 files changed, 950 insertions(+), 40 deletions(-)
