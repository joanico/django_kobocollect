# Enketo Express and Kobo Toolbox Guide

## Table of Contents
1. [Overview](#overview)
2. [What is Kobo Toolbox?](#what-is-kobo-toolbox)
3. [What is Enketo Express?](#what-is-enketo-express)
4. [How They Work Together](#how-they-work-together)
5. [Setting Up Enketo Express](#setting-up-enketo-express)
6. [Setting Up Kobo Toolbox Integration](#setting-up-kobo-toolbox-integration)
7. [Importing Forms from Kobo](#importing-forms-from-kobo)
8. [XLSForm to XML Workflow](#xlsform-to-xml-workflow)
9. [Troubleshooting](#troubleshooting)

---

## Overview

This guide explains how to set up and use **Enketo Express** and **Kobo Toolbox** with your Django application. These two tools work together to provide a complete form management and data collection solution.

### Quick Answer

- **Kobo Toolbox** = Backend storage and management (stores forms and data)
- **Enketo Express** = Frontend form filling interface (user-facing tool)
- **You use Enketo to fill out forms** - it's the user-facing tool
- **Kobo is for importing/syncing** - it's the data source/destination

---

## What is Kobo Toolbox?

**Kobo Toolbox** is a data collection platform that:
- **Stores form definitions** (the XForm XML templates)
- **Stores submitted data** (all the responses from filled forms)
- **Provides an API** to import/export forms and data
- **Manages users and permissions**
- **Provides analytics and reporting**

Think of Kobo as the **database/server** that holds everything.

### Key Features
- Form builder interface
- Data storage and management
- API access for integration
- User management and permissions
- Data export and analytics

---

## What is Enketo Express?

**Enketo Express** is a web form engine that:
- **Renders forms** in a browser (converts XForm XML into interactive web forms)
- **Allows users to fill out forms** with a user-friendly interface
- **Validates data** as users type
- **Works offline** (can save data locally and sync later)
- **Handles form submissions** and sends them back to the server

Think of Enketo as the **user interface** for filling out forms.

### Key Features
- Modern, responsive form interface
- Offline data collection
- Built-in validation
- User-friendly interface
- Works in any modern browser

---

## How They Work Together

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   Kobo Toolbox  │         │  Django Backend  │         │ Enketo Express  │
│                 │         │                  │         │                 │
│ • Form Storage  │────────▶│ • Form Import    │────────▶│ • Form Rendering│
│ • Data Storage  │         │ • Data Processing│         │ • User Interface│
│ • API Access    │         │ • User Auth      │         │ • Data Entry    │
└─────────────────┘         └──────────────────┘         └─────────────────┘
         ▲                                                         │
         │                                                         │
         └─────────────────────────────────────────────────────────┘
                            (Submissions flow back)
```

### Data Flow

1. **Form Creation**: Forms are created in Kobo Toolbox
2. **Form Import**: Forms are imported into Django from Kobo
3. **Form Rendering**: Enketo Express renders forms for users
4. **Data Collection**: Users fill out forms using Enketo
5. **Data Submission**: Submissions are saved to Django
6. **Optional Sync**: Data can be synced back to Kobo if needed

---

## Setting Up Enketo Express

### Prerequisites

- Node.js 20+ (required for Enketo Express 7.6.0 in monorepo)
- yarn (package manager for the monorepo)
- Redis (for caching and sessions)

### Installation

#### Step 1: Install Node.js 20+

If you're using nvm (Node Version Manager):

```bash
# Install Node.js 20 (or later, up to 22)
nvm install 20

# Switch to Node 20
nvm use 20

# Verify version
node --version  # Should show v20.x.x or v22.x.x
```

#### Step 2: Install Yarn (if not already installed)

```bash
# Install yarn globally
npm install -g yarn

# Verify installation
yarn --version
```

#### Step 3: Install and Build Enketo Express (Monorepo)

```bash
# Navigate to the enketo monorepo root directory
cd django_api_enpoint/enketo

# Install dependencies for all packages in the monorepo
yarn install

# Build all packages (required before starting)
# This builds enketo-transformer, enketo-core, and enketo-express
yarn build
```

**Note:** The build process may take a few minutes. This is required because the monorepo packages need to be compiled before use.

#### Step 4: Configure Enketo

Create or edit `packages/enketo-express/config/config.json`:

```json
{
  "linked form and data server": {
    "name": "Django API",
    "server url": "http://localhost:8000",
    "api key": "dev_token_12345"
  },
  "port": 8005,
  "base path": "",
  "server": {
    "payload limit": "50mb"
  },
  "redis": {
    "main": {
      "host": "localhost",
      "port": 6379
    },
    "cache": {
      "host": "localhost",
      "port": 6379
    }
  }
}
```

**Important Notes:**
- The API key (`dev_token_12345`) is for local development only
- For production, use a secure API key
- The same API key must be set in Django's `.env` file as `ENKETO_API_TOKEN`
- The config file is located at `enketo/packages/enketo-express/config/config.json` (relative to the monorepo root)

#### Step 5: Start Redis

Enketo requires Redis to be running:

```bash
# macOS (using Homebrew)
brew services start redis

# Linux
sudo systemctl start redis

# Verify Redis is running
redis-cli ping  # Should return: PONG
```

#### Step 6: Start Enketo Express

You have two options to start Enketo Express:

**Option A: From monorepo root (Recommended)**
```bash
# Make sure you're using Node 20+
nvm use 20

# Start Enketo Express using yarn workspace
cd django_api_enpoint/enketo
yarn workspace enketo-express start
```

**Option B: From enketo-express package directory**
```bash
# Make sure you're using Node 20+
nvm use 20

# Navigate to the enketo-express package
cd django_api_enpoint/enketo/packages/enketo-express

# Start Enketo Express
yarn start
```

Enketo Express will start on `http://localhost:8005`

### Verifying Enketo is Working

```bash
# Test Enketo is running
curl http://localhost:8005
# Should return HTML page
```

### Stopping Enketo Express

- Press `Ctrl+C` in the terminal where Enketo is running to stop it

#### If port is already in use:

```bash
# Find and kill the process using port 8005
kill $(lsof -ti :8005)

# Or kill all Enketo processes
pkill -f "yarn.*enketo-express"

# Verify port is free
lsof -i :8005  # Should return nothing
```

---

## Setting Up Kobo Toolbox Integration

### Prerequisites

- Kobo Toolbox account
- API token from Kobo Toolbox

### Getting Your Kobo API Token

1. Log in to [Kobo Toolbox](https://kf.kobotoolbox.org/)
2. Go to **Account Settings** → **API Tokens**
3. Copy your API token

### Getting Your Kobo Asset ID

The Asset ID is a unique identifier for each form/project in Kobo Toolbox.

#### Method 1: From Kobo URL (Easiest)

1. Go to your form in Kobo Toolbox
2. Look at the URL in your browser:
   ```
   https://kf.kobotoolbox.org/#/forms/aWN5dGyNjJSL8nZwxqh4E8
                                    ^^^^^^^^^^^^^^^^^^^^
                                    This is your Asset ID
   ```

#### Method 2: Using Kobo API

```bash
curl -H "Authorization: Token YOUR_ACCESS_TOKEN" \
  "https://kf.kobotoolbox.org/api/v2/assets/"
```

Look for the `uid` field in the response - that's your Asset ID.

### Configuring Django

Add to your `.env` file:

```bash
# Kobo Toolbox Configuration
KOBO_API_BASE_URL=https://kf.kobotoolbox.org/api/v2
ACCESS_TOKEN=your_kobo_api_token_here
KOBO_DEFAULT_ASSET_ID=your_asset_id_here
```

### Verifying Configuration

```bash
python manage.py shell
```

```python
from api.services import KoboService

service = KoboService()
data = service.get_apis()
print(f"Found {len(data.get('results', []))} records")
```

---

## Importing Forms from Kobo

There are **two methods** to import forms from Kobo into Django:

### Method 1: Automatic Import via Kobo API (Recommended)

**Best for:** Multiple forms, bulk import, ongoing sync

#### Setup

1. Ensure `ACCESS_TOKEN` is set in your `.env` file
2. Restart Django server

#### Steps

1. Go to `http://localhost:8000/kobo/import/`
2. You'll see a list of all forms available in your Kobo account
3. For each form, click **"Import Form"** to import it
4. Click **"Re-import"** to update an existing form with the latest version
5. Click **"Import Submissions"** to import all submissions for a form

#### Pros
- ✅ Automatic - fetches everything from Kobo API
- ✅ Fast - import multiple forms quickly
- ✅ Accurate - no copy/paste errors
- ✅ Bulk import - can import many forms at once
- ✅ Auto-updates - can re-import to get latest version
- ✅ Import submissions - can also import existing data
- ✅ User-friendly - nice web interface with buttons

#### Cons
- ❌ Requires API setup - need to configure API token
- ❌ Needs internet - must be connected to Kobo API
- ❌ Less control - can't edit XML before importing

### Method 2: Manual Import via Django Admin

**Best for:** Few forms, one-time import, need to modify XML

#### Steps

1. **Get XML from Kobo**:
   - Log into Kobo Toolbox website
   - Go to your form
   - Click "More Options" (⋮) → **"Download"** → **"XForm XML"**
   - Or export as XLSForm and convert to XML (see below)

2. **Import into Django Admin**:
   - Go to `http://localhost:8000/admin/`
   - Navigate to **API** → **Form definitions**
   - Click **"Add Form definition"**
   - Fill in:
     - **Name**: Form name
     - **Kobo ID**: Asset ID from Kobo (found in form URL)
     - **Version**: Form version (e.g., "1.0")
     - **XML Content**: Paste the entire XML here
     - **OR XLSForm File**: Upload XLSForm file directly (auto-converts to XML)
   - Click **"Save"**

#### Pros
- ✅ No API setup required
- ✅ Full control - you see exactly what XML you're importing
- ✅ Can edit XML - you can modify the XML before importing
- ✅ Works offline - once you have the XML, you don't need Kobo access
- ✅ Simple - just copy and paste

#### Cons
- ❌ Manual work - you have to do it step by step for each form
- ❌ Time consuming - takes time to copy/paste for multiple forms
- ❌ Error prone - easy to make mistakes copying XML
- ❌ No automatic updates - if Kobo form changes, you must manually update
- ❌ No bulk import - must do one form at a time

### Which Method Should You Use?

- **Use Kobo API Integration** if:
  - You have multiple forms (3+)
  - You want to import submissions too
  - You want to keep forms synced with Kobo
  - You want a faster, easier process
  - You have Kobo API access

- **Use Django Admin (Manual)** if:
  - You only have 1-2 forms
  - You want to modify the XML before importing
  - You don't have Kobo API access
  - You're doing a one-time import
  - You prefer full manual control

---

## XLSForm to XML Workflow

### Understanding XLSForm vs XForm XML

- **XLSForm (XLS)** = Excel-based format for **building/designing** forms
- **XForm XML** = Standard format that Enketo and Django need

**Key Difference:**
```
XLSForm (XLS) → [Convert] → XForm XML → [Import to Django] → Use with Enketo
```

### Complete Workflow

#### Step 1: Create/Edit Form in Kobo Toolbox

1. Log into [Kobo Toolbox](https://kf.kobotoolbox.org/)
2. Create a new form or edit existing form
3. Design your form using the form builder interface
4. Save your changes

#### Step 2: Get the XForm XML

You have **two options**:

**Option A: Download XML from Kobo Web Interface**
1. Go to your form in Kobo Toolbox
2. Click **"More Options"** menu (⋮) or **"Settings"**
3. Look for **"Download"** or **"Export"**
4. Select **"XForm XML"** (NOT XLSForm)
5. Download the XML file

**Option B: Export XLSForm and Convert to XML**
1. Export XLSForm from Kobo: Click "More Options" (⋮) → **"Export to XLSForm"**
2. Convert XLSForm to XForm XML:
   - **Method 1**: Upload XLSForm back to Kobo, then download XML
   - **Method 2**: Use pyxform (Python tool):
     ```bash
     pip install pyxform
     xls2xform your_form.xls output.xml
     ```
   - **Method 3**: Upload XLSForm directly in Django Admin (auto-converts)

#### Step 3: Import into Django

**Option A: Upload XLSForm Directly (Recommended)** ⭐

1. Go to Django Admin: `http://localhost:8000/admin/`
2. Navigate to **API** → **Form definitions**
3. Click **"Add Form definition"**
4. Fill in the form:
   - **Name**: Your form name
   - **Kobo ID**: The asset ID from Kobo
   - **Version**: Form version
   - **XLSForm File**: Click "Choose File" and select your .xls or .xlsx file
5. Click **"Save"**
   - The XLSForm will be automatically converted to XML!
   - No manual conversion needed!

**Note**: Requires `pyxform` package. Install with: `pip install pyxform`

**Option B: Paste XML Manually**

1. Go to Django Admin: `http://localhost:8000/admin/`
2. Navigate to **API** → **Form definitions**
3. Click **"Add Form definition"**
4. Fill in the form:
   - **Name**: Your form name
   - **Kobo ID**: The asset ID from Kobo
   - **Version**: Form version
   - **XML Content**: Paste the entire XML content
5. Click **"Save"**

#### Step 4: Use Enketo to Fill Forms

1. Go to Forms List: `http://localhost:8000/forms/`
2. Click on your form
3. Click **"Fill New Form"**
4. Enketo opens and you can fill out the form!

### Quick Reference

| Format | Purpose | Can Use in Django? |
|--------|---------|-------------------|
| **XLSForm (XLS)** | Building/designing forms | ❌ No (must convert) |
| **XForm XML** | Form definition for Enketo | ✅ Yes |
| **XLS (Data)** | Submission data export | ❌ No (this is data, not form) |

---

## Troubleshooting

### Enketo Express Issues

#### Error: "Enketo Service Unavailable"

**Cause:** Enketo Express is not running or not accessible

**Fix:**
1. Check Enketo is running: `curl http://localhost:8005`
2. Check `ENKETO_URL` in Django settings matches Enketo port
3. Restart Enketo Express

#### Error: "Connection Refused" (Redis)

**Cause:** Redis not running or wrong port

**Fix:**
1. Check Redis: `redis-cli ping` (should return: PONG)
2. If not running:
   - macOS: `brew services start redis`
   - Linux: `sudo systemctl start redis`
3. Verify `config/config.json` uses port 6379 for both Redis instances

#### Error: "Port 8005 Already in Use"

**Fix:**
```bash
# Find and kill the process
kill $(lsof -ti :8005)

# Or use a different port in config.json
```

#### Error: "Wrong Node version"

**Fix:**
```bash
# Make sure you're using Node 20 or later
nvm use 20
node --version  # Should show v20.x.x or v22.x.x
```

#### Error: "Payload Limit Exceeded"

**Fix:**
1. Increase payload limit in `enketo/packages/enketo-express/config/config.json`:
   ```json
   "payload limit": "100mb"
   ```
   Note: `payload limit` should be at the root level of the config, not nested under `server`.
2. **Restart Enketo** after changing config
3. Verify config is loaded

### Kobo Toolbox Issues

#### Error: "Kobo Not Configured"

**Fix:**
- Make sure `ACCESS_TOKEN` is set in your `.env` file
- Restart Django server after setting the token
- Check that the token is valid in Kobo

#### Error: "Error Fetching Forms"

**Fix:**
- Verify your API token is correct
- Check your internet connection
- Make sure you have access to the forms in Kobo
- Check Django logs for detailed error messages

#### Error: "Asset not found" or 404 Error

**Fix:**
- Double-check the Asset ID from the URL
- Make sure you're using the correct access token
- Verify the asset is accessible in your Kobo account

### Configuration Checklist

**Enketo Express:**
- [ ] Redis running on port 6379
- [ ] Enketo Express running on port 8005
- [ ] `enketo/packages/enketo-express/config/config.json` has correct Redis ports (6379 for both)
- [ ] Node.js 20+ is active (`nvm use 20`)
- [ ] Yarn is installed (`yarn --version`)
- [ ] Dependencies installed from monorepo root (`yarn install` completed)
- [ ] All packages built (`yarn build` completed successfully)

**Django:**
- [ ] `.env` file has `ENKETO_URL=http://localhost:8005`
- [ ] `.env` file has `ENKETO_API_TOKEN` (matches Enketo config)
- [ ] `.env` file has `ACCESS_TOKEN` (Kobo API token)
- [ ] Django settings.py loads environment variables
- [ ] Django server running on port 8000

**Kobo Toolbox:**
- [ ] API token is valid
- [ ] Asset ID is correct
- [ ] Forms are published/deployed in Kobo

---

## Summary

- **Kobo Toolbox** = Backend storage and management
- **Enketo Express** = Frontend form filling interface
- **You use Enketo to fill out forms** - it's the user-facing tool
- **Kobo is for importing/syncing** - it's the data source/destination

Both work together seamlessly in your Django application!

### Next Steps

1. Set up Enketo Express:
   - Install Node.js 20+ and yarn
   - Navigate to `django_api_enpoint/enketo` (monorepo root)
   - Run `yarn install` to install dependencies
   - Run `yarn build` to build all packages
   - Configure `packages/enketo-express/config/config.json`
   - Start with `yarn workspace enketo-express start`
2. Configure Kobo integration (get API token, set in `.env`)
3. Import forms from Kobo (use API integration or manual import)
4. Use Enketo to fill forms (go to `/forms/` and click "Fill New Form")

### Important Notes

- **Monorepo Structure**: Enketo Express is now part of the Enketo monorepo. Always work from the monorepo root (`django_api_enpoint/enketo`) when installing or building.
- **Yarn Workspaces**: Use `yarn workspace enketo-express <command>` to run commands for enketo-express from the monorepo root.
- **Build Required**: You must run `yarn build` after `yarn install` before starting Enketo Express. This builds all packages (enketo-transformer, enketo-core, enketo-express).

