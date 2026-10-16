
````md
# Clone This Repository Using SSH
````


## 1. Check whether you already have an SSH key

Open **Git Bash** and run:

```bash
ls -al ~/.ssh
````

Look for files like these:

```bash
id_ed25519
id_ed25519.pub
```

* `id_ed25519` is your private key
* `id_ed25519.pub` is your public key

If these files already exist, you can skip to Step 4.

---

## 2. Generate a new SSH key if needed

If you do not already have an SSH key on your system, run:

```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

When prompted, press **Enter** to use the default file location.

You can also press **Enter** to skip the passphrase, or set one if you want extra security.

---

## 3. Start the SSH agent and add your key

Run the following commands:

```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
```

---

## 4. Open and copy your public key

Now open your public key by running:

```bash
cat ~/.ssh/id_ed25519.pub
```

Copy the entire output.

---

## 5. Add your public key to GitHub

On GitHub:

1. Open **Settings**
2. Go to **SSH and GPG keys**
3. Click **New SSH key**
4. Paste your copied public key
5. Click **Save**

---

## 6. Clone the repository

Open **Git Bash** in the folder where you want to place the project.

You can either:

* right-click and open Git Bash directly in that folder, or
* use the `cd` command to move to the desired location

Then run:

```bash
git clone git@github.com:gauravlabs/SkillBridge.git
```

This will create the project folder in your current location.

---

## 7. Get the latest updates

After cloning, move into the project folder and pull the latest changes:

```bash
cd SkillBridge
git pull origin main
```

This ensures your local copy is up to date with the main branch.
