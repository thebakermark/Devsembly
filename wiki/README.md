# Publishing the Devsembly wiki

The `wiki/` directory is the version-controlled source for the GitHub Wiki.

After the main repository exists and its Wiki feature is enabled, clone the wiki repository and copy these Markdown files into it:

```bash
git clone https://github.com/OWNER/devsembly.wiki.git
cp -R devsembly/wiki/*.md devsembly.wiki/
cd devsembly.wiki
git add .
git commit -m "docs: publish initial Devsembly wiki"
git push origin master
```

GitHub may use `main` or `master` for the wiki repository depending on how it is initialized. Confirm the active branch before pushing.
