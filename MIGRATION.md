# Migration Notes

## additionnal.students → additional.students (PR #88)

A typo in the student SSH key directory name was corrected. Operators who ran a
deployment before this fix will have the old directory name on disk.

**Automatic:** the `credentials.generate` role detects and renames the old
directory on the next run (`ansible-playbook site.yml ...`).

**Manual (if needed):**
```bash
find config/ -type d -name "additionnal.students" \
  -execdir mv {} additional.students \;
```
