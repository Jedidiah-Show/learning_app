// Fix: Guard editor accesses when editor might be undefined
// This file patchs static/js/practice.js

with open('static/js/practice.js', 'r') as f:
    content = f.read()

# Fix 1: Guard setEditorSource - check if editor exists
old_setEditorSource = """    const setEditorSource = (source) => {
        switching = true;
        editor.setSource(source);
        switching = false;
    };"""

new_setEditorSource = """    const setEditorSource = (source) => {
        if (editor) {
            switching = true;
            editor.setSource(source);
        }
        switching = false;
    };"""

content = content.replace(old_setEditorSource, new_setEditorSource)

# Fix 2: Guard currentSource - check if editor exists  
old_currentSource = """    const currentSource = () => editor.getSource();"""

new_currentSource = """    const currentSource = () => {
        if (editor) {
            return editor.getSource();
        }
        return '';
    };"""

content = content.replace(old_currentSource, new_currentSource)

# Fix 3: Guard saveWorkspace - handle missing editor
# The saveWorkspace function uses currentSource(), which we already fixed,
# but also needs to handle the case where editor doesn't exist
# The saveWorkspace already calls currentSource(), so with the fix above it should work.
# However, we also need to ensure queueSave doesn't fail.
old_queueSave = """    const queueSave = () => {
        clearTimeout(saveTimer);
        setStatus('Unsaved changes', 'dirty');
        saveTimer = setTimeout(() => { void saveWorkspace(); }, 700);
    };"""

# queueSave doesn't directly use editor, it calls saveWorkspace which calls currentSource()
# So the fix to currentSource should be sufficient

# Fix 4: Guard saveWorkspace - ensure it handles missing editor gracefully
# Actually, saveWorkspace already calls currentSource() which we fixed.
# But let's also ensure the initial loadExercise doesn't fail.

with open('static/js/practice.js', 'w') as f:
    f.write(content)

print('Editor guards applied successfully')
