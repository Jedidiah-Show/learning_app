import {defaultKeymap, historyKeymap, indentWithTab} from '@codemirror/commands';
import {EditorState, Compartment} from '@codemirror/state';
import {autocompletion, closeBrackets} from '@codemirror/autocomplete';
import {EditorView, keymap, lineNumbers, highlightActiveLine, highlightActiveLineGutter, highlightSpecialChars, drawSelection} from '@codemirror/view';
import {foldGutter, foldKeymap, matchBrackets} from '@codemirror/language';

export const PYTHON_EDITOR_FONT = '"JetBrains Mono", "Fira Code", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace';

// Inert placeholder used until the lazily loaded Python language compartment
// is reconfigured; replaced by the real language once the dynamic import lands.
const inertLanguagePlaceholder = EditorView.theme({}, {dark: true});

// VS Code Dark+ inspired editor theme.
export const VSCODE_DARK_EDITOR_THEME = EditorView.theme({
    '&': {color: '#d4d4d4', backgroundColor: '#1e1e1e'},
    '.cm-content': {
        caretColor: '#aeafad',
        backgroundColor: '#1e1e1e',
        fontFamily: PYTHON_EDITOR_FONT,
    },
    '.cm-cursor, .cm-dropCursor': {borderLeftColor: '#aeafad'},
    '.cm-gutters': {backgroundColor: '#1e1e1e', color: '#6e7681', border: 'none'},
    '.cm-activeLine': {backgroundColor: '#282828'},
    '.cm-activeLineGutter': {backgroundColor: '#37373d'},
    '.cm-selectionBackground, .cm-content ::selection': {backgroundColor: '#264f78'},
    '.cm-matchingBracket': {backgroundColor: '#04395e'},
    '.cm-nonmatchingBracket': {backgroundColor: '#f14c4c'},
}, {dark: true});

// VS Code Light+ inspired editor theme.
export const VSCODE_LIGHT_EDITOR_THEME = EditorView.theme({
    '&': {color: '#1f1f1f', backgroundColor: '#ffffff'},
    '.cm-content': {caretColor: '#000000', backgroundColor: '#ffffff', fontFamily: PYTHON_EDITOR_FONT},
    '.cm-cursor, .cm-dropCursor': {borderLeftColor: '#000000'},
    '.cm-gutters': {backgroundColor: '#ffffff', color: '#237893', border: 'none'},
    '.cm-activeLine': {backgroundColor: '#f3f3f3'},
    '.cm-activeLineGutter': {backgroundColor: '#e8e8e8'},
    '.cm-selectionBackground, .cm-content ::selection': {backgroundColor: '#add6ff'},
    '.cm-matchingBracket': {backgroundColor: '#3a5f8a'},
    '.cm-nonmatchingBracket': {backgroundColor: '#f14c4c'},
}, {dark: false});

/**
Create the shared Python CodeMirror 6 editor.

The heavy Python language is loaded lazily through a compartment so the initial
editor bundle stays small; the editor renders line numbers and the VS Code-style
theme immediately and upgrades once the language chunk resolves.

Options:
  - theme: 'dark' | 'light' (defaults to 'dark', VS Code Dark+ look)
  - initialDoc: starting document
  - onChange(source: string): called for user-driven document changes
  - onCursorChange(line: number, col: number): called for cursor/selection updates
  - runCommand(): invoked by Mod-Enter (run/save flow)
  - saveCommand(): invoked by Mod-S (save flow)
*/
export function createPythonEditor(host, options = {}) {
    const {
        theme = 'dark',
        initialDoc = '',
        onChange = null,
        onCursorChange = null,
        runCommand = null,
        saveCommand = null,
    } = options;

    const themeCompartment = new Compartment();
    const languageCompartment = new Compartment();
    const initialTheme = theme === 'light' ? VSCODE_LIGHT_EDITOR_THEME : VSCODE_DARK_EDITOR_THEME;

    const handleUpdate = (update) => {
        if (update.docChanged && update.userEvent !== 'programmatic' && onChange) {
            onChange(update.state.doc.toString());
        }
        const cursor = update.state.selection.main;
        const line = update.state.doc.lineAt(cursor).number;
        const col = cursor.character + 1;
        if (onCursorChange) onCursorChange(line, col);
    };

    const bindings = [
        ...defaultKeymap.filter((binding) => binding.key !== 'Mod-Enter'),
        ...historyKeymap,
        ...foldKeymap,
        {key: 'Mod-Enter', run: () => { if (runCommand) runCommand(); return true; }},
        {key: 'Mod-s', run: () => { if (saveCommand) saveCommand(); return true; }},
        indentWithTab,
    ];

    const editor = new EditorView({
        state: EditorState.create({
            doc: initialDoc,
            extensions: [
                lineNumbers(),
                languageCompartment.of(inertLanguagePlaceholder),
                themeCompartment.of(initialTheme),
                history(),
                closeBrackets,
                autocompletion(),
                matchBrackets,
                foldGutter(),
                foldKeymap,
                EditorView.lineWrapping,
                EditorView.highlightActiveLine,
                EditorView.highlightActiveLineGutter,
                EditorView.highlightSpecialChars,
                EditorView.drawSelection,
                EditorView.updateListener.of(handleUpdate),
                keymap.of(bindings),
            ],
        }),
        parent: host,
    });

    const languageReady = (async () => {
        const languageModule = await import('@codemirror/lang-python');
        editor.dispatch({
            effects: languageCompartment.reconfigure(languageModule.python()),
        });
    })();
    return {
        editor,
        getSource: () => editor.state.doc.toString(),
        setSource: (source) => {
            editor.dispatch({
                changes: {from: 0, to: editor.state.doc.length, insert: source},
                userEvent: 'programmatic',
            });
        },
        focus: () => editor.focus(),
        requestMeasure: () => editor.requestMeasure(),
        setTheme: (mode) => {
            editor.dispatch({
                effects: themeCompartment.reconfigure(
                    mode === 'light' ? VSCODE_LIGHT_EDITOR_THEME : VSCODE_DARK_EDITOR_THEME,
                ),
            });
        },
        languageReady,
    };
}
