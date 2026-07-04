# Deploying the Portfolio to Azure at pete.peerslate.com

*Written 2026-07-02 · For Pete, doing this from the Mac · Estimated time: 1–2 hours (most of it waiting)*

---

## The big picture (read this first)

Right now your site only runs on your own computer. To put it on the internet, three separate things have to work together:

1. **Azure App Service** — a computer in Microsoft's datacenter that runs your Flask app 24/7. Think of it as "renting a machine that runs `app.py` forever."
2. **GitHub** — Azure doesn't copy files off your Mac. Instead, it pulls your code from your GitHub repo. Every time you push to the branch you connect, Azure automatically redeploys. This is called **continuous deployment**, and it fits perfectly with your "everything ends up in GitHub" workflow.
3. **Porkbun DNS** — you own PeerSlate.com at Porkbun. DNS is the internet's phone book: we'll add an entry saying "pete.peerslate.com → Pete's Azure app." That's what makes it a *subdomain* (a "subsite" in the way that scales to your multi-tenant plan — later, other customers just get their own subdomain entries).

The flow of a visitor's request after we're done:

```
Visitor types pete.peerslate.com
        ↓
Porkbun DNS says "that lives at <your-app>.azurewebsites.net"
        ↓
Azure App Service receives the request and runs your Flask app
        ↓
Flask returns the page (and /api/chat calls the Claude API when needed)
```

**Why a subdomain and not peerslate.com/pete?** A subdomain needs one DNS record — 5 minutes of work. A path like peerslate.com/pete requires a "reverse proxy" server that inspects every URL and forwards traffic, which only makes sense once the main PeerSlate site exists. Subdomains are also how real multi-tenant products (e.g., yourname.substack.com) do it.

**What it costs:** the Basic B1 plan is roughly **$13/month** (billed hourly, region-dependent). It's the cheapest tier that allows a custom domain + free SSL certificate. You can delete or scale it down anytime — nothing here locks you in.

---

## Part 0 — Before you start (on the Mac)

Azure will deploy from **one branch** of your GitHub repo. You're currently on `feature/my-story-page` with a few uncommitted changes. The cleanest setup is to deploy from `main`, so `main` becomes "what the public sees" and feature branches stay your workshop.

1. Open Terminal in the portfolio folder (in VS Code: **Terminal → New Terminal**).
2. Save all open files first (**Cmd+S** in each tab), then commit your current work:
   ```bash
   git add .
   git commit -m "Session work before Azure deployment"
   git push
   ```
3. Merge your feature branch into main and push it:
   ```bash
   git checkout main
   git pull
   git merge feature/my-story-page
   git push
   ```
   *(If `git merge` reports conflicts, stop and ask Claude for help — don't guess.)*

**Three checks that are already done** (verified 2026-07-02, listed so you know *why* they matter):

- ✅ `requirements.txt` exists — Azure reads this file and runs `pip install -r requirements.txt` on its server, exactly like you do on a new machine.
- ✅ `.env` is in `.gitignore` — your API key never touches GitHub. Azure gets the key a different way (Part 3).
- ✅ Your app is in `app.py` with a variable named `app` — Azure's Python setup auto-detects this and runs it with **gunicorn**, a production-grade web server. (Flask's built-in server, the thing that prints "development server, do not use in production," is only for your Mac. Gunicorn is the grown-up version, and Azure provides it — you don't install it.)

---

## Part 1 — Create the Web App in Azure

1. Go to **https://portal.azure.com** and sign in.
2. Click **Create a resource** (the big **+** on the home page) → search for **Web App** → click **Create**.
3. Fill in the **Basics** tab:

   | Field | What to enter | Why |
   |---|---|---|
   | Subscription | Your subscription (probably the only one listed) | Which billing account pays |
   | Resource group | Click **Create new** → name it `portfolio-rg` | A folder that groups everything for this project, so you can delete it all in one shot later |
   | Name | Something like `peerslate-pete` | Becomes your temporary URL: `peerslate-pete-<random>.azurewebsites.net`. Must be globally unique. |
   | Publish | **Code** | We're giving Azure source code, not a Docker container |
   | Runtime stack | **Python 3.12** (or newest 3.x offered) | Matches what your app runs on |
   | Operating System | **Linux** | Python on App Service is Linux-only |
   | Region | **East US** or **East US 2** | Closest to Alabama = fastest for you and local visitors |

4. Under **Pricing plans** (may be labeled "App Service Plan"): click **Create new**, name it `portfolio-plan`, then **change the pricing tier to Basic B1**. The default is often a Premium tier (~$50+/mo) — do not skip this step. Free F1 won't work either: it doesn't allow custom domains.
5. Skip the other tabs for now (we'll wire up GitHub in Part 2 where it's easier to see what's happening). Click **Review + create** → **Create**.
6. Wait ~1 minute for "Your deployment is complete," then click **Go to resource**.

📌 On the app's **Overview** page, note the **Default domain** (like `peerslate-pete-abc123.eastus2.azurewebsites.net`). You'll need it twice later — this is your app's "real" address; the custom domain is just a pointer to it.

---

## Part 2 — Connect GitHub (continuous deployment)

1. In your Web App's left menu, click **Deployment Center** (under "Deployment").
2. **Source**: choose **GitHub**. Click **Authorize** and sign in as `petercarter19-hue` when asked.
3. Pick:
   - **Organization**: petercarter19-hue
   - **Repository**: portfolio
   - **Branch**: main
4. Leave the build provider as **GitHub Actions** and **Save** (top of the pane).

**What just happened (this part is worth understanding):** Azure created a file in your repo at `.github/workflows/…yml`. That file is a robot recipe: *"whenever anything is pushed to main → set up Python → pip install the requirements → package the app → ship it to Azure."* GitHub runs this robot on their servers for free. From now on, **pushing to main = deploying to the internet.** That's also why we keep experiments on feature branches.

5. Watch it work: go to https://github.com/petercarter19-hue/portfolio → **Actions** tab. You'll see a workflow running (yellow dot). Wait for the green checkmark (~3–5 minutes).

⚠️ Because Azure committed a new file to your repo, run `git pull` on your Mac (while on `main`) before your next local work session, or your next push will be rejected.

---

## Part 3 — Give Azure your Claude API key

Your `.env` file stays on your Mac (correctly — it's git-ignored). But that means the app running in Azure has **no API key** and the chatbot would return errors. Cloud platforms solve this with **application settings**: environment variables you type into the portal, stored encrypted, visible to your app only. `load_dotenv()` simply finds nothing in Azure and does no harm; the `anthropic` library reads the environment variable directly either way.

1. In your Web App's left menu: **Settings → Environment variables** (older portals call it "Configuration").
2. Under **App settings**, click **+ Add**:
   - **Name**: `ANTHROPIC_API_KEY`
   - **Value**: paste your key (copy it from the `.env` file on your Mac — open it in VS Code, copy the value after the `=` sign, nothing else)
3. Click **Apply**, then **Confirm**. The app restarts automatically (~30 seconds).

🔐 Never put the key itself in this guide, in a commit, or in chat. If it ever leaks, generate a new key at console.anthropic.com and update both `.env` and this setting.

---

## Part 4 — Test on the temporary URL

Open `https://<your-default-domain>` (from the Part 1 note) in a browser.

- **Site loads, all 7 pages work** → continue to Part 5.
- **Chatbot works** → your API key setting is correct.
- **"Application Error" page** → in the portal, go to **Monitoring → Log stream** and read the last lines; they usually name the problem (most often a package missing from requirements.txt or a typo in the app setting). Bring the error text to Claude.

Don't move on until this URL works — DNS problems and app problems are much easier to debug separately.

---

## Part 5 — Point pete.peerslate.com at Azure (Porkbun)

Two records are needed. The **CNAME** does the actual pointing; the **TXT** proves to Azure that you own the domain (so a stranger can't claim your subdomain on their Azure app).

First, get the values from Azure:

1. In your Web App: **Settings → Custom domains** → **+ Add custom domain**.
2. Choose: **All other domain services** (because Porkbun isn't Azure), TLS/SSL certificate = **App Service Managed Certificate** (the free one), certificate type = **SNI SSL**.
3. Type the domain: `pete.peerslate.com`.
4. The dialog now shows exactly two values — **leave this browser tab open**:
   - a **CNAME value** (your default domain, e.g. `peerslate-pete-abc123.eastus2.azurewebsites.net`)
   - a **Domain verification ID** (a long code)

Now, in a second tab, add them at Porkbun:

5. Go to **https://porkbun.com** → log in → **Domain Management** → find **peerslate.com** → click **DNS** (or the "DNS Records" gear).
6. Add record 1:
   - **Type**: `CNAME`
   - **Host**: `pete`  *(Porkbun appends .peerslate.com automatically — do not type the full domain)*
   - **Answer**: the default domain from the Azure dialog (no `https://`, no trailing slash)
   - **TTL**: leave the default
7. Add record 2:
   - **Type**: `TXT`
   - **Host**: `asuid.pete`
   - **Answer**: the Domain verification ID from the Azure dialog
8. While you're there: if Porkbun still has default "parked domain" records (an **ALIAS** or **CNAME** pointing to something like `pixie.porkbun.com`, especially one with Host `*`), they're leftovers from registration. A `*` (wildcard) record can shadow real subdomains — delete the wildcard one if validation fails in the next part.

DNS changes usually propagate in 5–30 minutes, occasionally longer.

---

## Part 6 — Validate in Azure and get free HTTPS

1. Back in the Azure **Add custom domain** dialog, click **Validate**. Two green checkmarks = success. (Red? Wait 10 more minutes for DNS and try again — this is the single most common "failure," and it's just impatience.)
2. Click **Add**.
3. Azure now issues a **free SSL certificate** for pete.peerslate.com (this is what makes the padlock/`https://` work, and it auto-renews forever). The Custom domains page may show "Securing…" for up to 15 minutes. Wait until the domain shows **Secured / Healthy**.

---

## Part 7 — Final test

Visit **https://pete.peerslate.com**:

- Padlock icon in the address bar ✅
- All pages load ✅
- Chatbot answers a question ✅

You're live. Send it to someone.

---

## From now on: your publishing workflow

```
Work on a feature branch  →  test locally at 127.0.0.1:5000
        ↓ when happy
Merge into main and push  →  GitHub Actions deploys automatically (~4 min)
        ↓
Changes are live at pete.peerslate.com
```

Check any deploy's status in the repo's **Actions** tab on GitHub.

---

## Part 8 — Point the root domain (peerslate.com apex + www) at Azure

*Added 2026-07-03. Why this became necessary: the `94389b5` "site address" commit changed `app.py` so `pete.peerslate.com` now redirects to `https://peerslate.com/petec` (the plan being: peerslate.com becomes the shared "PeerSlate" platform home, with Pete's own portfolio living under the `/petec` path). But peerslate.com's DNS was never pointed at Azure — it was still sitting on Porkbun's default "Easy Links" URL-forwarding product, which showed a generic "A Brand New Domain!" placeholder instead of the real site. Net effect: the redirect the app added sent every visitor into a dead end. This part finishes the setup so the code's assumption matches reality.*

This is the same idea as Part 5, done twice more — once for the bare/apex domain (`peerslate.com`), once for `www.peerslate.com`. The apex domain needs an **A** or **ALIAS** record instead of a CNAME, because the DNS spec doesn't allow a CNAME at the root of a domain.

1. **Azure — add both custom domains.** In the Web App's **Custom domains** page, click **+ Add custom domain** twice:
   - `peerslate.com` — Domain source **All other domain services**, TLS/SSL **App Service Managed Certificate** (SNI SSL). Azure will show an **A record IP** (or sometimes an ALIAS target) plus a **TXT verification ID** (host `asuid`).
   - `www.peerslate.com` — same settings. Azure shows a **CNAME value** (the same default domain as always) plus a **TXT verification ID** (host `asuid.www`).
   Keep both dialogs open — you need the values from each.

2. **Porkbun — turn off the parking/forwarding feature first.** Domain Management → peerslate.com → find **URL Forwarding** / **Easy Links** (a separate feature from DNS Records) → turn it off or delete the rule. This is the actual cause of the placeholder page — DNS records alone won't fix it while this is still on.

3. **Porkbun — clean up old records.** In DNS Records, delete any leftover default entries pointing at Porkbun's parking IPs (`52.33.207.7`, `44.230.85.241`) or with Host `*`.

4. **Porkbun — add the new records:**
   - Apex: **ALIAS** record, Host blank/`@`, Answer = the azurewebsites.net default domain (e.g. `peerslate-pete-d9hhdeerd7frg2gc.centralus-01.azurewebsites.net`) — unless Azure's dialog gave a plain IP instead, in which case use an **A** record with that IP.
   - Apex verification: **TXT**, Host `asuid`, Answer = the verification ID from Azure's peerslate.com dialog.
   - www: **CNAME**, Host `www`, Answer = the same azurewebsites.net default domain.
   - www verification: **TXT**, Host `asuid.www`, Answer = the verification ID from Azure's www.peerslate.com dialog.

5. **Validate in Azure.** Click **Validate** → **Add** on each dialog. Wait for "Secured/Healthy" (SSL can take up to 15 min) and allow 5–30 min for DNS propagation.

6. **Test:** `https://peerslate.com` should render the platform home (`peerslate.html`), `https://peerslate.com/petec` should render Pete's portfolio, and `https://pete.peerslate.com` should now redirect correctly into the real site instead of Porkbun's parking page.

No extra Azure cost — the existing Basic B1 plan already covers unlimited custom domain bindings and free managed certificates.

---

## Troubleshooting quick reference

| Symptom | Likely cause | Fix |
|---|---|---|
| "Application Error" on azurewebsites.net | App crashed at startup | Portal → **Log stream**; read the traceback |
| Chatbot returns "Something went wrong" | API key setting missing/typo | Re-check Part 3; name must be exactly `ANTHROPIC_API_KEY` |
| Validate button shows red X | DNS not propagated yet, or typo'd Host values | Wait 15 min; verify records at https://dnschecker.org (search `pete.peerslate.com`, type CNAME) |
| pete.peerslate.com shows Porkbun parking page | Wildcard/parking record interfering | Delete Porkbun's default `*` ALIAS/CNAME records (Part 5 step 8) |
| Certificate stuck on "Securing" >1 hr | CNAME points somewhere indirect | CNAME must point *directly* at the azurewebsites.net name |
| Push to main didn't deploy | Workflow failed | GitHub → Actions tab → click the red run → read the failed step |
| Site suddenly returns old content | Browser cache | Hard refresh: Cmd+Shift+R |

## Cost control

- **See charges:** portal → search "Cost Management" → Cost analysis.
- **Set a spending alert:** Cost Management → Budgets → create a $20/mo budget with an email alert — a nice safety net.
- **Tear everything down:** delete the `portfolio-rg` resource group — removes the app, the plan, and all charges in one action. Your code is safe in GitHub; you could redo this guide in 20 minutes.

## Notes for the future ("subsite" roadmap)

- The **root** peerslate.com and www.peerslate.com are wired up as of Part 8 (2026-07-03) — both point at the same `peerslate-pete` Azure app, with `app.py`'s `is_platform_hostname()` check deciding whether to render the platform home (`peerslate.html`) or Pete's portfolio (`index.html`, under `/petec`).
- More tenants = more subdomains: each new customer is one CNAME + TXT pair at Porkbun pointing to their app (or eventually a wildcard `*.peerslate.com` to a single multi-tenant app — a later architecture conversation).
