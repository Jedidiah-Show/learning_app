import {
  Annotation,
  ChangeDesc,
  ChangeSet,
  Compartment,
  Direction,
  EditorSelection,
  EditorState,
  EditorView,
  Facet,
  IndentContext,
  NodeProp,
  StateEffect,
  StateField,
  Text,
  Transaction,
  autocompletion,
  closeBrackets,
  combineConfig,
  countColumn,
  findClusterBreak,
  foldGutter,
  foldKeymap,
  getIndentUnit,
  getIndentation,
  indentString,
  indentUnit,
  keymap,
  lineNumbers,
  matchBrackets,
  syntaxTree
} from "./chunk-NCOOGUYM.js";

// node_modules/@codemirror/commands/dist/index.js
var toggleComment = (target) => {
  let { state } = target, line = state.doc.lineAt(state.selection.main.from), config = getConfig(target.state, line.from);
  return config.line ? toggleLineComment(target) : config.block ? toggleBlockCommentByLine(target) : false;
};
function command(f, option) {
  return ({ state, dispatch }) => {
    if (state.readOnly)
      return false;
    let tr = f(option, state);
    if (!tr)
      return false;
    dispatch(state.update(tr));
    return true;
  };
}
var toggleLineComment = /* @__PURE__ */ command(
  changeLineComment,
  0
  /* CommentOption.Toggle */
);
var toggleBlockComment = /* @__PURE__ */ command(
  changeBlockComment,
  0
  /* CommentOption.Toggle */
);
var toggleBlockCommentByLine = /* @__PURE__ */ command(
  (o, s) => changeBlockComment(o, s, selectedLineRanges(s)),
  0
  /* CommentOption.Toggle */
);
function getConfig(state, pos) {
  let data = state.languageDataAt("commentTokens", pos, 1);
  return data.length ? data[0] : {};
}
var SearchMargin = 50;
function findBlockComment(state, { open, close }, from, to) {
  let textBefore = state.sliceDoc(from - SearchMargin, from);
  let textAfter = state.sliceDoc(to, to + SearchMargin);
  let spaceBefore = /\s*$/.exec(textBefore)[0].length, spaceAfter = /^\s*/.exec(textAfter)[0].length;
  let beforeOff = textBefore.length - spaceBefore;
  if (textBefore.slice(beforeOff - open.length, beforeOff) == open && textAfter.slice(spaceAfter, spaceAfter + close.length) == close) {
    return {
      open: { pos: from - spaceBefore, margin: spaceBefore && 1 },
      close: { pos: to + spaceAfter, margin: spaceAfter && 1 }
    };
  }
  let startText, endText;
  if (to - from <= 2 * SearchMargin) {
    startText = endText = state.sliceDoc(from, to);
  } else {
    startText = state.sliceDoc(from, from + SearchMargin);
    endText = state.sliceDoc(to - SearchMargin, to);
  }
  let startSpace = /^\s*/.exec(startText)[0].length, endSpace = /\s*$/.exec(endText)[0].length;
  let endOff = endText.length - endSpace - close.length;
  if (startText.slice(startSpace, startSpace + open.length) == open && endText.slice(endOff, endOff + close.length) == close) {
    return {
      open: {
        pos: from + startSpace + open.length,
        margin: /\s/.test(startText.charAt(startSpace + open.length)) ? 1 : 0
      },
      close: {
        pos: to - endSpace - close.length,
        margin: /\s/.test(endText.charAt(endOff - 1)) ? 1 : 0
      }
    };
  }
  return null;
}
function selectedLineRanges(state) {
  let ranges = [];
  for (let r of state.selection.ranges) {
    let fromLine = state.doc.lineAt(r.from);
    let toLine = r.to <= fromLine.to ? fromLine : state.doc.lineAt(r.to);
    if (toLine.from > fromLine.from && toLine.from == r.to)
      toLine = r.to == fromLine.to + 1 ? fromLine : state.doc.lineAt(r.to - 1);
    let last = ranges.length - 1;
    if (last >= 0 && ranges[last].to > fromLine.from)
      ranges[last].to = toLine.to;
    else
      ranges.push({ from: fromLine.from + /^\s*/.exec(fromLine.text)[0].length, to: toLine.to });
  }
  return ranges;
}
function changeBlockComment(option, state, ranges = state.selection.ranges) {
  let tokens = ranges.map((r) => getConfig(state, r.from).block);
  if (!tokens.every((c) => c))
    return null;
  let comments = ranges.map((r, i) => findBlockComment(state, tokens[i], r.from, r.to));
  if (option != 2 && !comments.every((c) => c)) {
    return { changes: state.changes(ranges.map((range, i) => {
      if (comments[i])
        return [];
      return [{ from: range.from, insert: tokens[i].open + " " }, { from: range.to, insert: " " + tokens[i].close }];
    })) };
  } else if (option != 1 && comments.some((c) => c)) {
    let changes = [];
    for (let i = 0, comment; i < comments.length; i++)
      if (comment = comments[i]) {
        let token = tokens[i], { open, close } = comment;
        changes.push({ from: open.pos - token.open.length, to: open.pos + open.margin }, { from: close.pos - close.margin, to: close.pos + token.close.length });
      }
    return { changes };
  }
  return null;
}
function changeLineComment(option, state, ranges = state.selection.ranges) {
  let lines = [];
  let prevLine = -1;
  ranges: for (let { from, to } of ranges) {
    let startI = lines.length, minIndent = 1e9, token;
    for (let pos = from; pos <= to; ) {
      let line = state.doc.lineAt(pos);
      if (token == void 0) {
        token = getConfig(state, line.from).line;
        if (!token)
          continue ranges;
      }
      if (line.from > prevLine && (from == to || to > line.from)) {
        prevLine = line.from;
        let indent = /^\s*/.exec(line.text)[0].length;
        let empty = indent == line.length;
        let comment = line.text.slice(indent, indent + token.length) == token ? indent : -1;
        if (indent < line.text.length && indent < minIndent)
          minIndent = indent;
        lines.push({ line, comment, token, indent, empty, single: false });
      }
      pos = line.to + 1;
    }
    if (minIndent < 1e9) {
      for (let i = startI; i < lines.length; i++)
        if (lines[i].indent < lines[i].line.text.length)
          lines[i].indent = minIndent;
    }
    if (lines.length == startI + 1)
      lines[startI].single = true;
  }
  if (option != 2 && lines.some((l) => l.comment < 0 && (!l.empty || l.single))) {
    let changes = [];
    for (let { line, token, indent, empty, single } of lines)
      if (single || !empty)
        changes.push({ from: line.from + indent, insert: token + " " });
    let changeSet = state.changes(changes);
    return { changes: changeSet, selection: state.selection.map(changeSet, 1) };
  } else if (option != 1 && lines.some((l) => l.comment >= 0)) {
    let changes = [];
    for (let { line, comment, token } of lines)
      if (comment >= 0) {
        let from = line.from + comment, to = from + token.length;
        if (line.text[to - line.from] == " ")
          to++;
        changes.push({ from, to });
      }
    return { changes };
  }
  return null;
}
var fromHistory = /* @__PURE__ */ Annotation.define();
var isolateHistory = /* @__PURE__ */ Annotation.define();
var invertedEffects = /* @__PURE__ */ Facet.define();
var historyConfig = /* @__PURE__ */ Facet.define({
  combine(configs) {
    return combineConfig(configs, {
      minDepth: 100,
      newGroupDelay: 500,
      joinToEvent: (_t, isAdjacent2) => isAdjacent2
    }, {
      minDepth: Math.max,
      newGroupDelay: Math.min,
      joinToEvent: (a, b) => (tr, adj) => a(tr, adj) || b(tr, adj)
    });
  }
});
var historyField_ = /* @__PURE__ */ StateField.define({
  create() {
    return HistoryState.empty;
  },
  update(state, tr) {
    let config = tr.state.facet(historyConfig);
    let fromHist = tr.annotation(fromHistory);
    if (fromHist) {
      let item = HistEvent.fromTransaction(tr, fromHist.selection), from = fromHist.side;
      let other = from == 0 ? state.undone : state.done;
      if (item)
        other = updateBranch(other, other.length, config.minDepth, item);
      else
        other = addSelection(other, tr.startState.selection);
      return new HistoryState(from == 0 ? fromHist.rest : other, from == 0 ? other : fromHist.rest);
    }
    let isolate = tr.annotation(isolateHistory);
    if (isolate == "full" || isolate == "before")
      state = state.isolate();
    if (tr.annotation(Transaction.addToHistory) === false)
      return !tr.changes.empty ? state.addMapping(tr.changes.desc) : state;
    let event = HistEvent.fromTransaction(tr);
    let time = tr.annotation(Transaction.time), userEvent = tr.annotation(Transaction.userEvent);
    if (event)
      state = state.addChanges(event, time, userEvent, config, tr);
    else if (tr.selection)
      state = state.addSelection(tr.startState.selection, time, userEvent, config.newGroupDelay);
    if (isolate == "full" || isolate == "after")
      state = state.isolate();
    return state;
  },
  toJSON(value) {
    return { done: value.done.map((e) => e.toJSON()), undone: value.undone.map((e) => e.toJSON()) };
  },
  fromJSON(json) {
    return new HistoryState(json.done.map(HistEvent.fromJSON), json.undone.map(HistEvent.fromJSON));
  }
});
function history(config = {}) {
  return [
    historyField_,
    historyConfig.of(config),
    EditorView.domEventHandlers({
      beforeinput(e, view) {
        let command2 = e.inputType == "historyUndo" ? undo : e.inputType == "historyRedo" ? redo : null;
        if (!command2)
          return false;
        e.preventDefault();
        return command2(view);
      }
    })
  ];
}
function cmd(side, selection) {
  return function({ state, dispatch }) {
    if (!selection && state.readOnly)
      return false;
    let historyState = state.field(historyField_, false);
    if (!historyState)
      return false;
    let tr = historyState.pop(side, state, selection);
    if (!tr)
      return false;
    dispatch(tr);
    return true;
  };
}
var undo = /* @__PURE__ */ cmd(0, false);
var redo = /* @__PURE__ */ cmd(1, false);
var undoSelection = /* @__PURE__ */ cmd(0, true);
var redoSelection = /* @__PURE__ */ cmd(1, true);
var HistEvent = class _HistEvent {
  constructor(changes, effects, mapped, startSelection, selectionsAfter) {
    this.changes = changes;
    this.effects = effects;
    this.mapped = mapped;
    this.startSelection = startSelection;
    this.selectionsAfter = selectionsAfter;
  }
  setSelAfter(after) {
    return new _HistEvent(this.changes, this.effects, this.mapped, this.startSelection, after);
  }
  toJSON() {
    var _a, _b, _c;
    return {
      changes: (_a = this.changes) === null || _a === void 0 ? void 0 : _a.toJSON(),
      mapped: (_b = this.mapped) === null || _b === void 0 ? void 0 : _b.toJSON(),
      startSelection: (_c = this.startSelection) === null || _c === void 0 ? void 0 : _c.toJSON(),
      selectionsAfter: this.selectionsAfter.map((s) => s.toJSON())
    };
  }
  static fromJSON(json) {
    return new _HistEvent(json.changes && ChangeSet.fromJSON(json.changes), [], json.mapped && ChangeDesc.fromJSON(json.mapped), json.startSelection && EditorSelection.fromJSON(json.startSelection), json.selectionsAfter.map(EditorSelection.fromJSON));
  }
  // This does not check `addToHistory` and such, it assumes the
  // transaction needs to be converted to an item. Returns null when
  // there are no changes or effects in the transaction.
  static fromTransaction(tr, selection) {
    let effects = none;
    for (let invert of tr.startState.facet(invertedEffects)) {
      let result = invert(tr);
      if (result.length)
        effects = effects.concat(result);
    }
    if (!effects.length && tr.changes.empty)
      return null;
    return new _HistEvent(tr.changes.invert(tr.startState.doc), effects, void 0, selection || tr.startState.selection, none);
  }
  static selection(selections) {
    return new _HistEvent(void 0, none, void 0, void 0, selections);
  }
};
function updateBranch(branch, to, maxLen, newEvent) {
  let start = to + 1 > maxLen + 20 ? to - maxLen - 1 : 0;
  let newBranch = branch.slice(start, to);
  newBranch.push(newEvent);
  return newBranch;
}
function isAdjacent(a, b) {
  let ranges = [], isAdjacent2 = false;
  a.iterChangedRanges((f, t) => ranges.push(f, t));
  b.iterChangedRanges((_f, _t, f, t) => {
    for (let i = 0; i < ranges.length; ) {
      let from = ranges[i++], to = ranges[i++];
      if (t >= from && f <= to)
        isAdjacent2 = true;
    }
  });
  return isAdjacent2;
}
function eqSelectionShape(a, b) {
  return a.ranges.length == b.ranges.length && a.ranges.filter((r, i) => r.empty != b.ranges[i].empty).length === 0;
}
function conc(a, b) {
  return !a.length ? b : !b.length ? a : a.concat(b);
}
var none = [];
var MaxSelectionsPerEvent = 200;
function addSelection(branch, selection) {
  if (!branch.length) {
    return [HistEvent.selection([selection])];
  } else {
    let lastEvent = branch[branch.length - 1];
    let sels = lastEvent.selectionsAfter.slice(Math.max(0, lastEvent.selectionsAfter.length - MaxSelectionsPerEvent));
    if (sels.length && sels[sels.length - 1].eq(selection))
      return branch;
    sels.push(selection);
    return updateBranch(branch, branch.length - 1, 1e9, lastEvent.setSelAfter(sels));
  }
}
function popSelection(branch) {
  let last = branch[branch.length - 1];
  let newBranch = branch.slice();
  newBranch[branch.length - 1] = last.setSelAfter(last.selectionsAfter.slice(0, last.selectionsAfter.length - 1));
  return newBranch;
}
function addMappingToBranch(branch, mapping) {
  if (!branch.length)
    return branch;
  let length = branch.length, selections = none;
  while (length) {
    let event = mapEvent(branch[length - 1], mapping, selections);
    if (event.changes && !event.changes.empty || event.effects.length) {
      let result = branch.slice(0, length);
      result[length - 1] = event;
      return result;
    } else {
      mapping = event.mapped;
      length--;
      selections = event.selectionsAfter;
    }
  }
  return selections.length ? [HistEvent.selection(selections)] : none;
}
function mapEvent(event, mapping, extraSelections) {
  let selections = conc(event.selectionsAfter.length ? event.selectionsAfter.map((s) => s.map(mapping)) : none, extraSelections);
  if (!event.changes)
    return HistEvent.selection(selections);
  let mappedChanges = event.changes.map(mapping), before = mapping.mapDesc(event.changes, true);
  let fullMapping = event.mapped ? event.mapped.composeDesc(before) : before;
  return new HistEvent(mappedChanges, StateEffect.mapEffects(event.effects, mapping), fullMapping, event.startSelection.map(before), selections);
}
var joinableUserEvent = /^(input\.type|delete)($|\.)/;
var HistoryState = class _HistoryState {
  constructor(done, undone, prevTime = 0, prevUserEvent = void 0) {
    this.done = done;
    this.undone = undone;
    this.prevTime = prevTime;
    this.prevUserEvent = prevUserEvent;
  }
  isolate() {
    return this.prevTime ? new _HistoryState(this.done, this.undone) : this;
  }
  addChanges(event, time, userEvent, config, tr) {
    let done = this.done, lastEvent = done[done.length - 1];
    if (lastEvent && lastEvent.changes && !lastEvent.changes.empty && event.changes && (!userEvent || joinableUserEvent.test(userEvent)) && (!lastEvent.selectionsAfter.length && time - this.prevTime < config.newGroupDelay && config.joinToEvent(tr, isAdjacent(lastEvent.changes, event.changes)) || // For compose (but not compose.start) events, always join with previous event
    userEvent == "input.type.compose")) {
      done = updateBranch(done, done.length - 1, config.minDepth, new HistEvent(event.changes.compose(lastEvent.changes), conc(StateEffect.mapEffects(event.effects, lastEvent.changes), lastEvent.effects), lastEvent.mapped, lastEvent.startSelection, none));
    } else {
      done = updateBranch(done, done.length, config.minDepth, event);
    }
    return new _HistoryState(done, none, time, userEvent);
  }
  addSelection(selection, time, userEvent, newGroupDelay) {
    let last = this.done.length ? this.done[this.done.length - 1].selectionsAfter : none;
    if (last.length > 0 && time - this.prevTime < newGroupDelay && userEvent == this.prevUserEvent && userEvent && /^select($|\.)/.test(userEvent) && eqSelectionShape(last[last.length - 1], selection))
      return this;
    return new _HistoryState(addSelection(this.done, selection), this.undone, time, userEvent);
  }
  addMapping(mapping) {
    return new _HistoryState(addMappingToBranch(this.done, mapping), addMappingToBranch(this.undone, mapping), this.prevTime, this.prevUserEvent);
  }
  pop(side, state, onlySelection) {
    let branch = side == 0 ? this.done : this.undone;
    if (branch.length == 0)
      return null;
    let event = branch[branch.length - 1], selection = event.selectionsAfter[0] || (event.startSelection ? event.startSelection.map(event.changes.invertedDesc, 1) : state.selection);
    if (onlySelection && event.selectionsAfter.length) {
      return state.update({
        selection: event.selectionsAfter[event.selectionsAfter.length - 1],
        annotations: fromHistory.of({ side, rest: popSelection(branch), selection }),
        userEvent: side == 0 ? "select.undo" : "select.redo",
        scrollIntoView: true
      });
    } else if (!event.changes) {
      return null;
    } else {
      let rest = branch.length == 1 ? none : branch.slice(0, branch.length - 1);
      if (event.mapped)
        rest = addMappingToBranch(rest, event.mapped);
      return state.update({
        changes: event.changes,
        selection: event.startSelection,
        effects: event.effects,
        annotations: fromHistory.of({ side, rest, selection }),
        filter: false,
        userEvent: side == 0 ? "undo" : "redo",
        scrollIntoView: true
      });
    }
  }
};
HistoryState.empty = /* @__PURE__ */ new HistoryState(none, none);
var historyKeymap = [
  { key: "Mod-z", run: undo, preventDefault: true },
  { key: "Mod-y", mac: "Mod-Shift-z", run: redo, preventDefault: true },
  { linux: "Ctrl-Shift-z", run: redo, preventDefault: true },
  { key: "Mod-u", run: undoSelection, preventDefault: true },
  { key: "Alt-u", mac: "Mod-Shift-u", run: redoSelection, preventDefault: true }
];
function updateSel(sel, by) {
  return EditorSelection.create(sel.ranges.map(by), sel.mainIndex);
}
function setSel(state, selection) {
  return state.update({ selection, scrollIntoView: true, userEvent: "select" });
}
function moveSel({ state, dispatch }, how) {
  let selection = updateSel(state.selection, how);
  if (selection.eq(state.selection, true))
    return false;
  dispatch(setSel(state, selection));
  return true;
}
function rangeEnd(range, forward) {
  return EditorSelection.cursor(forward ? range.to : range.from);
}
function cursorByChar(view, forward) {
  return moveSel(view, (range) => range.empty ? view.moveByChar(range, forward) : rangeEnd(range, forward));
}
function ltrAtCursor(view) {
  return view.textDirectionAt(view.state.selection.main.head) == Direction.LTR;
}
var cursorCharLeft = (view) => cursorByChar(view, !ltrAtCursor(view));
var cursorCharRight = (view) => cursorByChar(view, ltrAtCursor(view));
function cursorByGroup(view, forward) {
  return moveSel(view, (range) => range.empty ? view.moveByGroup(range, forward) : rangeEnd(range, forward));
}
var cursorGroupLeft = (view) => cursorByGroup(view, !ltrAtCursor(view));
var cursorGroupRight = (view) => cursorByGroup(view, ltrAtCursor(view));
var segmenter = typeof Intl != "undefined" && Intl.Segmenter ? /* @__PURE__ */ new Intl.Segmenter(void 0, { granularity: "word" }) : null;
function interestingNode(state, node, bracketProp) {
  if (node.type.prop(bracketProp))
    return true;
  let len = node.to - node.from;
  return len && (len > 2 || /[^\s,.;:]/.test(state.sliceDoc(node.from, node.to))) || node.firstChild;
}
function moveBySyntax(state, start, forward) {
  let pos = syntaxTree(state).resolveInner(start.head);
  let bracketProp = forward ? NodeProp.closedBy : NodeProp.openedBy;
  for (let at = start.head; ; ) {
    let next = forward ? pos.childAfter(at) : pos.childBefore(at);
    if (!next)
      break;
    if (interestingNode(state, next, bracketProp))
      pos = next;
    else
      at = forward ? next.to : next.from;
  }
  let bracket = pos.type.prop(bracketProp), match, newPos;
  if (bracket && (match = forward ? matchBrackets(state, pos.from, 1) : matchBrackets(state, pos.to, -1)) && match.matched)
    newPos = forward ? match.end.to : match.end.from;
  else
    newPos = forward ? pos.to : pos.from;
  return EditorSelection.cursor(newPos, forward ? -1 : 1);
}
var cursorSyntaxLeft = (view) => moveSel(view, (range) => moveBySyntax(view.state, range, !ltrAtCursor(view)));
var cursorSyntaxRight = (view) => moveSel(view, (range) => moveBySyntax(view.state, range, ltrAtCursor(view)));
function cursorByLine(view, forward) {
  return moveSel(view, (range) => {
    if (!range.empty)
      return rangeEnd(range, forward);
    let moved = view.moveVertically(range, forward);
    return moved.head != range.head ? moved : view.moveToLineBoundary(range, forward);
  });
}
var cursorLineUp = (view) => cursorByLine(view, false);
var cursorLineDown = (view) => cursorByLine(view, true);
function pageInfo(view) {
  let selfScroll = view.scrollDOM.clientHeight < view.scrollDOM.scrollHeight - 2;
  let marginTop = 0, marginBottom = 0, height;
  if (selfScroll) {
    for (let source of view.state.facet(EditorView.scrollMargins)) {
      let margins = source(view);
      if (margins === null || margins === void 0 ? void 0 : margins.top)
        marginTop = Math.max(margins === null || margins === void 0 ? void 0 : margins.top, marginTop);
      if (margins === null || margins === void 0 ? void 0 : margins.bottom)
        marginBottom = Math.max(margins === null || margins === void 0 ? void 0 : margins.bottom, marginBottom);
    }
    height = view.scrollDOM.clientHeight - marginTop - marginBottom;
  } else {
    height = (view.dom.ownerDocument.defaultView || window).innerHeight;
  }
  return {
    marginTop,
    marginBottom,
    selfScroll,
    height: Math.max(view.defaultLineHeight, height - 5)
  };
}
function cursorByPage(view, forward) {
  let page = pageInfo(view);
  let { state } = view, selection = updateSel(state.selection, (range) => {
    return range.empty ? view.moveVertically(range, forward, page.height) : rangeEnd(range, forward);
  });
  if (selection.eq(state.selection))
    return false;
  let effect;
  if (page.selfScroll) {
    let startPos = view.coordsAtPos(state.selection.main.head);
    let scrollRect = view.scrollDOM.getBoundingClientRect();
    let scrollTop = scrollRect.top + page.marginTop, scrollBottom = scrollRect.bottom - page.marginBottom;
    if (startPos && startPos.top > scrollTop && startPos.bottom < scrollBottom)
      effect = EditorView.scrollIntoView(selection.main.head, { y: "start", yMargin: startPos.top - scrollTop });
  }
  view.dispatch(setSel(state, selection), { effects: effect });
  return true;
}
var cursorPageUp = (view) => cursorByPage(view, false);
var cursorPageDown = (view) => cursorByPage(view, true);
function moveByLineBoundary(view, start, forward) {
  let line = view.lineBlockAt(start.head), moved = view.moveToLineBoundary(start, forward);
  if (moved.head == start.head && moved.head != (forward ? line.to : line.from))
    moved = view.moveToLineBoundary(start, forward, false);
  if (!forward && moved.head == line.from && line.length) {
    let space = /^\s*/.exec(view.state.sliceDoc(line.from, Math.min(line.from + 100, line.to)))[0].length;
    if (space && start.head != line.from + space)
      moved = EditorSelection.cursor(line.from + space);
  }
  return moved;
}
var cursorLineBoundaryForward = (view) => moveSel(view, (range) => moveByLineBoundary(view, range, true));
var cursorLineBoundaryBackward = (view) => moveSel(view, (range) => moveByLineBoundary(view, range, false));
var cursorLineBoundaryLeft = (view) => moveSel(view, (range) => moveByLineBoundary(view, range, !ltrAtCursor(view)));
var cursorLineBoundaryRight = (view) => moveSel(view, (range) => moveByLineBoundary(view, range, ltrAtCursor(view)));
var cursorLineStart = (view) => moveSel(view, (range) => view.moveToLineBoundary(range, false, false));
var cursorLineEnd = (view) => moveSel(view, (range) => view.moveToLineBoundary(range, true, false));
function toMatchingBracket(state, dispatch, extend) {
  let found = false, selection = updateSel(state.selection, (range) => {
    let matching = matchBrackets(state, range.head, -1) || matchBrackets(state, range.head, 1) || range.head > 0 && matchBrackets(state, range.head - 1, 1) || range.head < state.doc.length && matchBrackets(state, range.head + 1, -1);
    if (!matching || !matching.end)
      return range;
    found = true;
    let head = matching.start.from == range.head ? matching.end.to : matching.end.from;
    return extend ? EditorSelection.range(range.anchor, head) : EditorSelection.cursor(head);
  });
  if (!found)
    return false;
  dispatch(setSel(state, selection));
  return true;
}
var cursorMatchingBracket = ({ state, dispatch }) => toMatchingBracket(state, dispatch, false);
function extendSel(target, forward, how) {
  let selection = updateSel(target.state.selection, (range) => {
    if (range.undirectional && range.head >= range.anchor != forward)
      range = EditorSelection.range(range.head, range.anchor);
    let head = how(range);
    return EditorSelection.range(range.anchor, head.head, head.goalColumn, head.bidiLevel || void 0, head.assoc);
  });
  if (selection.eq(target.state.selection))
    return false;
  target.dispatch(setSel(target.state, selection));
  return true;
}
function selectByChar(view, forward) {
  return extendSel(view, forward, (range) => view.moveByChar(range, forward));
}
var selectCharLeft = (view) => selectByChar(view, !ltrAtCursor(view));
var selectCharRight = (view) => selectByChar(view, ltrAtCursor(view));
function selectByGroup(view, forward) {
  return extendSel(view, forward, (range) => view.moveByGroup(range, forward));
}
var selectGroupLeft = (view) => selectByGroup(view, !ltrAtCursor(view));
var selectGroupRight = (view) => selectByGroup(view, ltrAtCursor(view));
var selectSyntaxLeft = (view) => {
  let forward = !ltrAtCursor(view);
  return extendSel(view, forward, (range) => moveBySyntax(view.state, range, forward));
};
var selectSyntaxRight = (view) => {
  let forward = ltrAtCursor(view);
  return extendSel(view, forward, (range) => moveBySyntax(view.state, range, forward));
};
function selectByLine(view, forward) {
  return extendSel(view, forward, (range) => view.moveVertically(range, forward));
}
var selectLineUp = (view) => selectByLine(view, false);
var selectLineDown = (view) => selectByLine(view, true);
function selectByPage(view, forward) {
  return extendSel(view, forward, (range) => view.moveVertically(range, forward, pageInfo(view).height));
}
var selectPageUp = (view) => selectByPage(view, false);
var selectPageDown = (view) => selectByPage(view, true);
var selectLineBoundaryForward = (view) => extendSel(view, true, (range) => moveByLineBoundary(view, range, true));
var selectLineBoundaryBackward = (view) => extendSel(view, false, (range) => moveByLineBoundary(view, range, false));
var selectLineBoundaryLeft = (view) => {
  let forward = !ltrAtCursor(view);
  return extendSel(view, forward, (range) => moveByLineBoundary(view, range, forward));
};
var selectLineBoundaryRight = (view) => {
  let forward = ltrAtCursor(view);
  return extendSel(view, forward, (range) => moveByLineBoundary(view, range, forward));
};
var selectLineStart = (view) => extendSel(view, false, (range) => EditorSelection.cursor(view.lineBlockAt(range.head).from));
var selectLineEnd = (view) => extendSel(view, true, (range) => EditorSelection.cursor(view.lineBlockAt(range.head).to));
var cursorDocStart = ({ state, dispatch }) => {
  dispatch(setSel(state, { anchor: 0 }));
  return true;
};
var cursorDocEnd = ({ state, dispatch }) => {
  dispatch(setSel(state, { anchor: state.doc.length }));
  return true;
};
var selectDocStart = ({ state, dispatch }) => {
  dispatch(setSel(state, { anchor: state.selection.main.anchor, head: 0 }));
  return true;
};
var selectDocEnd = ({ state, dispatch }) => {
  dispatch(setSel(state, { anchor: state.selection.main.anchor, head: state.doc.length }));
  return true;
};
var selectAll = ({ state, dispatch }) => {
  dispatch(state.update({ selection: { anchor: 0, head: state.doc.length }, userEvent: "select" }));
  return true;
};
var selectLine = ({ state, dispatch }) => {
  let ranges = selectedLineBlocks(state).map(({ from, to }) => EditorSelection.undirectionalRange(from, Math.min(to + 1, state.doc.length)));
  dispatch(state.update({ selection: EditorSelection.create(ranges), userEvent: "select" }));
  return true;
};
var selectParentSyntax = ({ state, dispatch }) => {
  let selection = updateSel(state.selection, (range) => {
    let tree = syntaxTree(state), stack = tree.resolveStack(range.from, 1);
    if (range.empty) {
      let stackBefore = tree.resolveStack(range.from, -1);
      if (stackBefore.node.from >= stack.node.from && stackBefore.node.to <= stack.node.to)
        stack = stackBefore;
    }
    for (let cur = stack; cur; cur = cur.next) {
      let { node } = cur;
      if ((node.from < range.from && node.to >= range.to || node.to > range.to && node.from <= range.from) && cur.next)
        return EditorSelection.undirectionalRange(node.from, node.to);
    }
    return range;
  });
  if (selection.eq(state.selection))
    return false;
  dispatch(setSel(state, selection));
  return true;
};
function addCursorVertically(view, forward) {
  let { state } = view, sel = state.selection, ranges = state.selection.ranges.slice();
  for (let range of state.selection.ranges) {
    let line = state.doc.lineAt(range.head);
    if (forward ? line.to < view.state.doc.length : line.from > 0)
      for (let cur = range; ; ) {
        let next = view.moveVertically(cur, forward);
        if (next.head < line.from || next.head > line.to) {
          if (!ranges.some((r) => r.head == next.head))
            ranges.push(next);
          break;
        } else if (next.head == cur.head) {
          break;
        } else {
          cur = next;
        }
      }
  }
  if (ranges.length == sel.ranges.length)
    return false;
  view.dispatch(setSel(state, EditorSelection.create(ranges, ranges.length - 1)));
  return true;
}
var addCursorAbove = (view) => addCursorVertically(view, false);
var addCursorBelow = (view) => addCursorVertically(view, true);
var simplifySelection = ({ state, dispatch }) => {
  let cur = state.selection, selection = null;
  if (cur.ranges.length > 1)
    selection = EditorSelection.create([cur.main]);
  else if (!cur.main.empty)
    selection = EditorSelection.create([EditorSelection.cursor(cur.main.head)]);
  if (!selection)
    return false;
  dispatch(setSel(state, selection));
  return true;
};
function deleteBy(target, by) {
  if (target.state.readOnly)
    return false;
  let event = "delete.selection", { state } = target;
  let changes = state.changeByRange((range) => {
    let { from, to } = range;
    if (from == to) {
      let towards = by(range);
      if (towards < from) {
        event = "delete.backward";
        towards = skipAtomic(target, towards, false);
      } else if (towards > from) {
        event = "delete.forward";
        towards = skipAtomic(target, towards, true);
      }
      from = Math.min(from, towards);
      to = Math.max(to, towards);
    } else {
      from = skipAtomic(target, from, false);
      to = skipAtomic(target, to, true);
    }
    return from == to ? { range } : { changes: { from, to }, range: EditorSelection.cursor(from, from < range.head ? -1 : 1) };
  });
  if (changes.changes.empty)
    return false;
  target.dispatch(state.update(changes, {
    scrollIntoView: true,
    userEvent: event,
    effects: event == "delete.selection" ? EditorView.announce.of(state.phrase("Selection deleted")) : void 0
  }));
  return true;
}
function skipAtomic(target, pos, forward) {
  if (target instanceof EditorView)
    for (let ranges of target.state.facet(EditorView.atomicRanges).map((f) => f(target)))
      ranges.between(pos, pos, (from, to) => {
        if (from < pos && to > pos)
          pos = forward ? to : from;
      });
  return pos;
}
var deleteByChar = (target, forward, byIndentUnit) => deleteBy(target, (range) => {
  let pos = range.from, { state } = target, line = state.doc.lineAt(pos), before, targetPos;
  if (byIndentUnit && !forward && pos > line.from && pos < line.from + 200 && !/[^ \t]/.test(before = line.text.slice(0, pos - line.from))) {
    if (before[before.length - 1] == "	")
      return pos - 1;
    let col = countColumn(before, state.tabSize), drop = col % getIndentUnit(state) || getIndentUnit(state);
    for (let i = 0; i < drop && before[before.length - 1 - i] == " "; i++)
      pos--;
    targetPos = pos;
  } else {
    targetPos = findClusterBreak(line.text, pos - line.from, forward, forward) + line.from;
    if (targetPos == pos && line.number != (forward ? state.doc.lines : 1))
      targetPos += forward ? 1 : -1;
    else if (!forward && /[\ufe00-\ufe0f]/.test(line.text.slice(targetPos - line.from, pos - line.from)))
      targetPos = findClusterBreak(line.text, targetPos - line.from, false, false) + line.from;
  }
  return targetPos;
});
var deleteCharBackward = (view) => deleteByChar(view, false, true);
var deleteCharForward = (view) => deleteByChar(view, true, false);
var deleteByGroup = (target, forward) => deleteBy(target, (range) => {
  let pos = range.head, { state } = target, line = state.doc.lineAt(pos);
  let categorize = state.charCategorizer(pos);
  for (let cat = null; ; ) {
    if (pos == (forward ? line.to : line.from)) {
      if (pos == range.head && line.number != (forward ? state.doc.lines : 1))
        pos += forward ? 1 : -1;
      break;
    }
    let next = findClusterBreak(line.text, pos - line.from, forward) + line.from;
    let nextChar = line.text.slice(Math.min(pos, next) - line.from, Math.max(pos, next) - line.from);
    let nextCat = categorize(nextChar);
    if (cat != null && nextCat != cat)
      break;
    if (nextChar != " " || pos != range.head)
      cat = nextCat;
    pos = next;
  }
  return pos;
});
var deleteGroupBackward = (target) => deleteByGroup(target, false);
var deleteGroupForward = (target) => deleteByGroup(target, true);
var deleteToLineEnd = (view) => deleteBy(view, (range) => {
  let lineEnd = view.lineBlockAt(range.head).to;
  return range.head < lineEnd ? lineEnd : Math.min(view.state.doc.length, range.head + 1);
});
var deleteLineBoundaryBackward = (view) => deleteBy(view, (range) => {
  let lineStart = view.moveToLineBoundary(range, false).head;
  return range.head > lineStart ? lineStart : Math.max(0, range.head - 1);
});
var deleteLineBoundaryForward = (view) => deleteBy(view, (range) => {
  let lineStart = view.moveToLineBoundary(range, true).head;
  return range.head < lineStart ? lineStart : Math.min(view.state.doc.length, range.head + 1);
});
var splitLine = ({ state, dispatch }) => {
  if (state.readOnly)
    return false;
  let changes = state.changeByRange((range) => {
    return {
      changes: { from: range.from, to: range.to, insert: Text.of(["", ""]) },
      range: EditorSelection.cursor(range.from)
    };
  });
  dispatch(state.update(changes, { scrollIntoView: true, userEvent: "input" }));
  return true;
};
var transposeChars = ({ state, dispatch }) => {
  if (state.readOnly)
    return false;
  let changes = state.changeByRange((range) => {
    if (!range.empty || range.from == 0 || range.from == state.doc.length)
      return { range };
    let pos = range.from, line = state.doc.lineAt(pos);
    let from = pos == line.from ? pos - 1 : findClusterBreak(line.text, pos - line.from, false) + line.from;
    let to = pos == line.to ? pos + 1 : findClusterBreak(line.text, pos - line.from, true) + line.from;
    return {
      changes: { from, to, insert: state.doc.slice(pos, to).append(state.doc.slice(from, pos)) },
      range: EditorSelection.cursor(to)
    };
  });
  if (changes.changes.empty)
    return false;
  dispatch(state.update(changes, { scrollIntoView: true, userEvent: "move.character" }));
  return true;
};
function selectedLineBlocks(state) {
  let blocks = [], upto = -1;
  for (let range of state.selection.ranges) {
    let startLine = state.doc.lineAt(range.from), endLine = state.doc.lineAt(range.to);
    if (!range.empty && range.to == endLine.from)
      endLine = state.doc.lineAt(range.to - 1);
    if (upto >= startLine.number) {
      let prev = blocks[blocks.length - 1];
      prev.to = endLine.to;
      prev.ranges.push(range);
    } else {
      blocks.push({ from: startLine.from, to: endLine.to, ranges: [range] });
    }
    upto = endLine.number + 1;
  }
  return blocks;
}
function moveLine(state, dispatch, forward) {
  if (state.readOnly)
    return false;
  let changes = [], ranges = [];
  for (let block of selectedLineBlocks(state)) {
    if (forward ? block.to == state.doc.length : block.from == 0)
      continue;
    let nextLine = state.doc.lineAt(forward ? block.to + 1 : block.from - 1);
    let size = nextLine.length + 1;
    if (forward) {
      changes.push({ from: block.to, to: nextLine.to }, { from: block.from, insert: nextLine.text + state.lineBreak });
      for (let r of block.ranges)
        ranges.push(EditorSelection.range(Math.min(state.doc.length, r.anchor + size), Math.min(state.doc.length, r.head + size)));
    } else {
      changes.push({ from: nextLine.from, to: block.from }, { from: block.to, insert: state.lineBreak + nextLine.text });
      for (let r of block.ranges)
        ranges.push(EditorSelection.range(r.anchor - size, r.head - size));
    }
  }
  if (!changes.length)
    return false;
  dispatch(state.update({
    changes,
    scrollIntoView: true,
    selection: EditorSelection.create(ranges, state.selection.mainIndex),
    userEvent: "move.line"
  }));
  return true;
}
var moveLineUp = ({ state, dispatch }) => moveLine(state, dispatch, false);
var moveLineDown = ({ state, dispatch }) => moveLine(state, dispatch, true);
function copyLine(state, dispatch, forward) {
  if (state.readOnly)
    return false;
  let changes = [];
  for (let block of selectedLineBlocks(state)) {
    if (forward)
      changes.push({ from: block.from, insert: state.doc.slice(block.from, block.to) + state.lineBreak });
    else
      changes.push({ from: block.to, insert: state.lineBreak + state.doc.slice(block.from, block.to) });
  }
  let changeSet = state.changes(changes);
  dispatch(state.update({
    changes: changeSet,
    selection: state.selection.map(changeSet, forward ? 1 : -1),
    scrollIntoView: true,
    userEvent: "input.copyline"
  }));
  return true;
}
var copyLineUp = ({ state, dispatch }) => copyLine(state, dispatch, false);
var copyLineDown = ({ state, dispatch }) => copyLine(state, dispatch, true);
var deleteLine = (view) => {
  if (view.state.readOnly)
    return false;
  let { state } = view, changes = state.changes(selectedLineBlocks(state).map(({ from, to }) => {
    if (from > 0)
      from--;
    else if (to < state.doc.length)
      to++;
    return { from, to };
  }));
  let selection = updateSel(state.selection, (range) => {
    let dist = void 0;
    if (view.lineWrapping) {
      let block = view.lineBlockAt(range.head), pos = view.coordsAtPos(range.head, range.assoc || 1);
      if (pos)
        dist = block.bottom + view.documentTop - pos.bottom + view.defaultLineHeight / 2;
    }
    return view.moveVertically(range, true, dist);
  }).map(changes);
  view.dispatch({ changes, selection, scrollIntoView: true, userEvent: "delete.line" });
  return true;
};
function isBetweenBrackets(state, pos) {
  if (/\(\)|\[\]|\{\}/.test(state.sliceDoc(pos - 1, pos + 1)))
    return { from: pos, to: pos };
  let context = syntaxTree(state).resolveInner(pos);
  let before = context.childBefore(pos), after = context.childAfter(pos), closedBy;
  if (before && after && before.to <= pos && after.from >= pos && (closedBy = before.type.prop(NodeProp.closedBy)) && closedBy.indexOf(after.name) > -1 && state.doc.lineAt(before.to).from == state.doc.lineAt(after.from).from && !/\S/.test(state.sliceDoc(before.to, after.from)))
    return { from: before.to, to: after.from };
  return null;
}
var insertNewlineAndIndent = /* @__PURE__ */ newlineAndIndent(false);
var insertBlankLine = /* @__PURE__ */ newlineAndIndent(true);
function newlineAndIndent(atEof) {
  return ({ state, dispatch }) => {
    if (state.readOnly)
      return false;
    let changes = state.changeByRange((range) => {
      let { from, to } = range, line = state.doc.lineAt(from);
      let explode = !atEof && from == to && isBetweenBrackets(state, from);
      if (atEof)
        from = to = (to <= line.to ? line : state.doc.lineAt(to)).to;
      let cx = new IndentContext(state, { simulateBreak: from, simulateDoubleBreak: !!explode });
      let indent = getIndentation(cx, from);
      if (indent == null)
        indent = countColumn(/^\s*/.exec(state.doc.lineAt(from).text)[0], state.tabSize);
      while (to < line.to && /\s/.test(line.text[to - line.from]))
        to++;
      if (explode)
        ({ from, to } = explode);
      else if (from > line.from && from < line.from + 100 && !/\S/.test(line.text.slice(0, from)))
        from = line.from;
      let insert = ["", indentString(state, indent)];
      if (explode)
        insert.push(indentString(state, cx.lineIndent(line.from, -1)));
      return {
        changes: { from, to, insert: Text.of(insert) },
        range: EditorSelection.cursor(from + 1 + insert[1].length)
      };
    });
    dispatch(state.update(changes, { scrollIntoView: true, userEvent: "input" }));
    return true;
  };
}
function changeBySelectedLine(state, f) {
  let atLine = -1;
  return state.changeByRange((range) => {
    let changes = [];
    for (let pos = range.from; pos <= range.to; ) {
      let line = state.doc.lineAt(pos);
      if (line.number > atLine && (range.empty || range.to > line.from)) {
        f(line, changes, range);
        atLine = line.number;
      }
      pos = line.to + 1;
    }
    let changeSet = state.changes(changes);
    return {
      changes,
      range: EditorSelection.range(changeSet.mapPos(range.anchor, 1), changeSet.mapPos(range.head, 1))
    };
  });
}
var indentSelection = ({ state, dispatch }) => {
  if (state.readOnly)
    return false;
  let updated = /* @__PURE__ */ Object.create(null);
  let context = new IndentContext(state, { overrideIndentation: (start) => {
    let found = updated[start];
    return found == null ? -1 : found;
  } });
  let changes = changeBySelectedLine(state, (line, changes2, range) => {
    let indent = getIndentation(context, line.from);
    if (indent == null)
      return;
    if (!/\S/.test(line.text))
      indent = 0;
    let cur = /^\s*/.exec(line.text)[0];
    let norm = indentString(state, indent);
    if (cur != norm || range.from < line.from + cur.length) {
      updated[line.from] = indent;
      changes2.push({ from: line.from, to: line.from + cur.length, insert: norm });
    }
  });
  if (!changes.changes.empty)
    dispatch(state.update(changes, { userEvent: "indent" }));
  return true;
};
var indentMore = ({ state, dispatch }) => {
  if (state.readOnly)
    return false;
  dispatch(state.update(changeBySelectedLine(state, (line, changes) => {
    changes.push({ from: line.from, insert: state.facet(indentUnit) });
  }), { userEvent: "input.indent" }));
  return true;
};
var indentLess = ({ state, dispatch }) => {
  if (state.readOnly)
    return false;
  dispatch(state.update(changeBySelectedLine(state, (line, changes) => {
    let space = /^\s*/.exec(line.text)[0];
    if (!space)
      return;
    let col = countColumn(space, state.tabSize), keep = 0;
    let insert = indentString(state, Math.max(0, col - getIndentUnit(state)));
    while (keep < space.length && keep < insert.length && space.charCodeAt(keep) == insert.charCodeAt(keep))
      keep++;
    changes.push({ from: line.from + keep, to: line.from + space.length, insert: insert.slice(keep) });
  }), { userEvent: "delete.dedent" }));
  return true;
};
var toggleTabFocusMode = (view) => {
  view.setTabFocusMode();
  return true;
};
var emacsStyleKeymap = [
  { key: "Ctrl-b", run: cursorCharLeft, shift: selectCharLeft, preventDefault: true },
  { key: "Ctrl-f", run: cursorCharRight, shift: selectCharRight },
  { key: "Ctrl-p", run: cursorLineUp, shift: selectLineUp },
  { key: "Ctrl-n", run: cursorLineDown, shift: selectLineDown },
  { key: "Ctrl-a", run: cursorLineStart, shift: selectLineStart },
  { key: "Ctrl-e", run: cursorLineEnd, shift: selectLineEnd },
  { key: "Ctrl-d", run: deleteCharForward },
  { key: "Ctrl-h", run: deleteCharBackward },
  { key: "Ctrl-k", run: deleteToLineEnd },
  { key: "Ctrl-Alt-h", run: deleteGroupBackward },
  { key: "Ctrl-o", run: splitLine },
  { key: "Ctrl-t", run: transposeChars },
  { key: "Ctrl-v", run: cursorPageDown }
];
var standardKeymap = /* @__PURE__ */ [
  { key: "ArrowLeft", run: cursorCharLeft, shift: selectCharLeft, preventDefault: true },
  { key: "Mod-ArrowLeft", mac: "Alt-ArrowLeft", run: cursorGroupLeft, shift: selectGroupLeft, preventDefault: true },
  { mac: "Cmd-ArrowLeft", run: cursorLineBoundaryLeft, shift: selectLineBoundaryLeft, preventDefault: true },
  { key: "ArrowRight", run: cursorCharRight, shift: selectCharRight, preventDefault: true },
  { key: "Mod-ArrowRight", mac: "Alt-ArrowRight", run: cursorGroupRight, shift: selectGroupRight, preventDefault: true },
  { mac: "Cmd-ArrowRight", run: cursorLineBoundaryRight, shift: selectLineBoundaryRight, preventDefault: true },
  { key: "ArrowUp", run: cursorLineUp, shift: selectLineUp, preventDefault: true },
  { mac: "Cmd-ArrowUp", run: cursorDocStart, shift: selectDocStart },
  { mac: "Ctrl-ArrowUp", run: cursorPageUp, shift: selectPageUp },
  { key: "ArrowDown", run: cursorLineDown, shift: selectLineDown, preventDefault: true },
  { mac: "Cmd-ArrowDown", run: cursorDocEnd, shift: selectDocEnd },
  { mac: "Ctrl-ArrowDown", run: cursorPageDown, shift: selectPageDown },
  { key: "PageUp", run: cursorPageUp, shift: selectPageUp },
  { key: "PageDown", run: cursorPageDown, shift: selectPageDown },
  { key: "Home", run: cursorLineBoundaryBackward, shift: selectLineBoundaryBackward, preventDefault: true },
  { key: "Mod-Home", run: cursorDocStart, shift: selectDocStart },
  { key: "End", run: cursorLineBoundaryForward, shift: selectLineBoundaryForward, preventDefault: true },
  { key: "Mod-End", run: cursorDocEnd, shift: selectDocEnd },
  { key: "Enter", run: insertNewlineAndIndent, shift: insertNewlineAndIndent },
  { key: "Mod-a", run: selectAll },
  { key: "Backspace", run: deleteCharBackward, shift: deleteCharBackward, preventDefault: true },
  { key: "Delete", run: deleteCharForward, preventDefault: true },
  { key: "Mod-Backspace", mac: "Alt-Backspace", run: deleteGroupBackward, preventDefault: true },
  { key: "Mod-Delete", mac: "Alt-Delete", run: deleteGroupForward, preventDefault: true },
  { mac: "Mod-Backspace", run: deleteLineBoundaryBackward, preventDefault: true },
  { mac: "Mod-Delete", run: deleteLineBoundaryForward, preventDefault: true }
].concat(/* @__PURE__ */ emacsStyleKeymap.map((b) => ({ mac: b.key, run: b.run, shift: b.shift })));
var defaultKeymap = /* @__PURE__ */ [
  { key: "Alt-ArrowLeft", mac: "Ctrl-ArrowLeft", run: cursorSyntaxLeft, shift: selectSyntaxLeft },
  { key: "Alt-ArrowRight", mac: "Ctrl-ArrowRight", run: cursorSyntaxRight, shift: selectSyntaxRight },
  { key: "Alt-ArrowUp", run: moveLineUp },
  { key: "Shift-Alt-ArrowUp", run: copyLineUp },
  { key: "Alt-ArrowDown", run: moveLineDown },
  { key: "Shift-Alt-ArrowDown", run: copyLineDown },
  { key: "Mod-Alt-ArrowUp", run: addCursorAbove },
  { key: "Mod-Alt-ArrowDown", run: addCursorBelow },
  { key: "Escape", run: simplifySelection },
  { key: "Mod-Enter", run: insertBlankLine },
  { key: "Alt-l", mac: "Ctrl-l", run: selectLine },
  { key: "Mod-i", run: selectParentSyntax, preventDefault: true },
  { key: "Mod-[", run: indentLess },
  { key: "Mod-]", run: indentMore },
  { key: "Mod-Alt-\\", run: indentSelection },
  { key: "Shift-Mod-k", run: deleteLine },
  { key: "Shift-Mod-\\", run: cursorMatchingBracket },
  { key: "Mod-/", run: toggleComment },
  { key: "Alt-A", mac: "Ctrl-A", run: toggleBlockComment },
  { key: "Ctrl-m", mac: "Shift-Alt-m", run: toggleTabFocusMode }
].concat(standardKeymap);
var indentWithTab = { key: "Tab", run: indentMore, shift: indentLess };

// static/js/python-editor.js
var PYTHON_EDITOR_FONT = '"JetBrains Mono", "Fira Code", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace';
var inertLanguagePlaceholder = EditorView.theme({}, { dark: true });
var VSCODE_DARK_EDITOR_THEME = EditorView.theme({
  "&": { color: "#d4d4d4", backgroundColor: "#1e1e1e" },
  ".cm-content": {
    caretColor: "#aeafad",
    backgroundColor: "#1e1e1e",
    fontFamily: PYTHON_EDITOR_FONT
  },
  ".cm-cursor, .cm-dropCursor": { borderLeftColor: "#aeafad" },
  ".cm-gutters": { backgroundColor: "#1e1e1e", color: "#6e7681", border: "none" },
  ".cm-activeLine": { backgroundColor: "#282828" },
  ".cm-activeLineGutter": { backgroundColor: "#37373d" },
  ".cm-selectionBackground, .cm-content ::selection": { backgroundColor: "#264f78" },
  ".cm-matchingBracket": { backgroundColor: "#04395e" },
  ".cm-nonmatchingBracket": { backgroundColor: "#f14c4c" }
}, { dark: true });
var VSCODE_LIGHT_EDITOR_THEME = EditorView.theme({
  "&": { color: "#1f1f1f", backgroundColor: "#ffffff" },
  ".cm-content": { caretColor: "#000000", backgroundColor: "#ffffff", fontFamily: PYTHON_EDITOR_FONT },
  ".cm-cursor, .cm-dropCursor": { borderLeftColor: "#000000" },
  ".cm-gutters": { backgroundColor: "#ffffff", color: "#237893", border: "none" },
  ".cm-activeLine": { backgroundColor: "#f3f3f3" },
  ".cm-activeLineGutter": { backgroundColor: "#e8e8e8" },
  ".cm-selectionBackground, .cm-content ::selection": { backgroundColor: "#add6ff" },
  ".cm-matchingBracket": { backgroundColor: "#3a5f8a" },
  ".cm-nonmatchingBracket": { backgroundColor: "#f14c4c" }
}, { dark: false });
function createPythonEditor(host, options = {}) {
  const {
    theme = "dark",
    initialDoc = "",
    onChange = null,
    onCursorChange = null,
    runCommand = null,
    saveCommand = null
  } = options;
  const themeCompartment = new Compartment();
  const languageCompartment = new Compartment();
  const initialTheme = theme === "light" ? VSCODE_LIGHT_EDITOR_THEME : VSCODE_DARK_EDITOR_THEME;
  const handleUpdate = (update) => {
    if (update.docChanged && update.userEvent !== "programmatic" && onChange) {
      onChange(update.state.doc.toString());
    }
    const cursor = update.state.selection.main;
    const line = update.state.doc.lineAt(cursor).number;
    const col = cursor.character + 1;
    if (onCursorChange) onCursorChange(line, col);
  };
  const bindings = [
    ...defaultKeymap.filter((binding) => binding.key !== "Mod-Enter"),
    ...historyKeymap,
    ...foldKeymap,
    { key: "Mod-Enter", run: () => {
      if (runCommand) runCommand();
      return true;
    } },
    { key: "Mod-s", run: () => {
      if (saveCommand) saveCommand();
      return true;
    } },
    indentWithTab
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
        keymap.of(bindings)
      ]
    }),
    parent: host
  });
  const languageReady = (async () => {
    const languageModule = await import("./dist-VWBRKAMX.js");
    editor.dispatch({
      effects: languageCompartment.reconfigure(languageModule.python())
    });
  })();
  return {
    editor,
    getSource: () => editor.state.doc.toString(),
    setSource: (source) => {
      editor.dispatch({
        changes: { from: 0, to: editor.state.doc.length, insert: source },
        userEvent: "programmatic"
      });
    },
    focus: () => editor.focus(),
    requestMeasure: () => editor.requestMeasure(),
    setTheme: (mode) => {
      editor.dispatch({
        effects: themeCompartment.reconfigure(
          mode === "light" ? VSCODE_LIGHT_EDITOR_THEME : VSCODE_DARK_EDITOR_THEME
        )
      });
    },
    languageReady
  };
}

// static/js/arena.js
var root = document.querySelector("[data-arena-workspace]");
if (root) {
  const loadUrl = root.dataset.loadUrl;
  const saveUrl = root.dataset.saveUrl;
  const submitUrl = root.dataset.submitUrl;
  const hintUrl = root.dataset.hintUrl;
  const editorialUrl = root.dataset.editorialUrl;
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || "";
  const editorHost = document.getElementById("arena-editor");
  const saveStatus = document.getElementById("arena-save-status");
  const output = document.getElementById("arena-output");
  const statusBar = document.getElementById("arena-statusbar");
  const statusPosition = document.getElementById("arena-statusbar-position");
  const runButton = document.getElementById("arena-run");
  const submitButton = document.getElementById("arena-submit");
  const customChecks = document.getElementById("arena-custom-checks");
  const hintOutput = document.getElementById("arena-hint-output");
  const themeButton = document.getElementById("arena-theme");
  const fullscreenButton = document.getElementById("arena-fullscreen");
  const resizeHandle = document.getElementById("arena-resize");
  const panels = document.getElementById("arena-panels");
  const resetButton = document.getElementById("arena-reset");
  const revealButton = document.getElementById("arena-reveal");
  const editorialPanel = document.getElementById("arena-editorial");
  const editorialCode = document.getElementById("arena-editorial-code");
  const editorialProse = document.getElementById("arena-editorial-prose");
  const iframe = document.getElementById("arena-sandbox");
  let problem = null;
  const editor = createPythonEditor(editorHost, {
    theme: "dark",
    onChange: (source) => {
      if (switching || source === savedSource) return;
      queueSave();
    },
    onCursorChange: (line, col) => {
      if (!statusPosition) return;
      statusPosition.textContent = `Ln ${line}, Col ${col}`;
    },
    runCommand: () => {
      void saveWorkspace().then(runChecks);
    },
    saveCommand: () => {
      void saveWorkspace();
    }
  });
  let savedSource = "";
  let saveTimer = null;
  let savePromise = null;
  let switching = false;
  let runnerReady = false;
  let runnerStarted = false;
  let runnerLoadTimeout = null;
  let queuedRun = false;
  let activeRunId = null;
  let nextRunId = 0;
  let runTimeout = null;
  let lightTheme = false;
  const setSaveStatus = (message, state = "") => {
    saveStatus.textContent = message;
    saveStatus.dataset.state = state;
  };
  const setOutput = (message, state = "idle") => {
    output.textContent = message;
    output.dataset.state = state;
  };
  const currentSource = () => editor.getSource();
  const setEditorSource = (source) => {
    switching = true;
    editor.setSource(source);
    switching = false;
  };
  themeButton.addEventListener("click", () => {
    lightTheme = !lightTheme;
    editor.setTheme(lightTheme ? "light" : "dark");
    themeButton.setAttribute("aria-pressed", String(lightTheme));
    themeButton.textContent = lightTheme ? "Dark editor" : "Light editor";
  });
  fullscreenButton.addEventListener("click", async () => {
    try {
      if (document.fullscreenElement === root) {
        await document.exitFullscreen();
      } else {
        await root.requestFullscreen();
      }
    } catch (error) {
      setOutput("Full-screen mode is unavailable in this browser.", "error");
    }
  });
  document.addEventListener("fullscreenchange", () => {
    fullscreenButton.textContent = document.fullscreenElement === root ? "Exit full screen" : "Full screen";
  });
  let resizeStart = null;
  let paneLeftWidth = null;
  resizeHandle.addEventListener("pointerdown", (event) => {
    const bounds = panels.getBoundingClientRect();
    resizeStart = {
      pointerId: event.pointerId,
      pointerX: event.clientX,
      leftWidth: paneLeftWidth ?? (bounds.width - 48) / 2,
      width: bounds.width
    };
    resizeHandle.setPointerCapture(event.pointerId);
  });
  resizeHandle.addEventListener("pointermove", (event) => {
    if (!resizeStart || resizeStart.pointerId !== event.pointerId) return;
    const gutter = 8;
    paneLeftWidth = Math.min(
      Math.max(resizeStart.leftWidth + event.clientX - resizeStart.pointerX, 280),
      resizeStart.width - gutter - 40 - 280
    );
    panels.style.gridTemplateColumns = `minmax(280px, ${paneLeftWidth}px) ${gutter}px minmax(280px, 1fr)`;
    resizeHandle.setAttribute(
      "aria-valuenow",
      String(Math.round(paneLeftWidth / (resizeStart.width - gutter - 40) * 100))
    );
  });
  const stopResize = () => {
    resizeStart = null;
  };
  resizeHandle.addEventListener("pointerup", stopResize);
  resizeHandle.addEventListener("pointercancel", stopResize);
  resizeHandle.addEventListener("keydown", (event) => {
    if (!["ArrowLeft", "ArrowRight"].includes(event.key)) return;
    event.preventDefault();
    const bounds = panels.getBoundingClientRect();
    paneLeftWidth = Math.min(
      Math.max((paneLeftWidth ?? (bounds.width - 48) / 2) + (event.key === "ArrowRight" ? 24 : -24), 280),
      bounds.width - 336
    );
    panels.style.gridTemplateColumns = `minmax(280px, ${paneLeftWidth}px) 8px minmax(280px, 1fr)`;
    resizeHandle.setAttribute(
      "aria-valuenow",
      String(Math.round(paneLeftWidth / (bounds.width - 48) * 100))
    );
  });
  const saveWorkspace = async () => {
    clearTimeout(saveTimer);
    if (savePromise) {
      const saved = await savePromise;
      if (!saved) return false;
      return currentSource() === savedSource ? true : saveWorkspace();
    }
    const source = currentSource();
    if (!problem || source === savedSource) return true;
    savePromise = (async () => {
      setSaveStatus("Saving\u2026", "saving");
      try {
        const response = await fetch(saveUrl, {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            "X-CSRF-Token": csrfToken
          },
          body: JSON.stringify({ source })
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(data.error || "Could not save your work.");
        }
        savedSource = source;
        setSaveStatus("Saved", "saved");
        if (currentSource() !== savedSource) queueSave();
        return true;
      } catch (error) {
        setSaveStatus(error.message || "Could not save your work.", "error");
        return false;
      } finally {
        savePromise = null;
      }
    })();
    return savePromise;
  };
  const queueSave = () => {
    clearTimeout(saveTimer);
    setSaveStatus("Unsaved changes", "dirty");
    saveTimer = setTimeout(() => {
      void saveWorkspace();
    }, 700);
  };
  const loadProblem = async () => {
    setSaveStatus("Loading saved work\u2026", "saving");
    try {
      const response = await fetch(loadUrl);
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "Could not load this problem.");
      }
      problem = data.problem;
      savedSource = data.source;
      setEditorSource(data.source);
      setSaveStatus(data.updated_at ? "Saved work loaded" : "Starter code loaded", "saved");
      runButton.disabled = !runnerReady;
      submitButton.disabled = false;
      void editor.languageReady;
    } catch (error) {
      setSaveStatus(error.message || "Could not load this problem.", "error");
      setOutput("The problem could not be loaded. Reload the page to try again.", "error");
    }
  };
  const startRunner = () => {
    if (runnerStarted) return;
    runnerStarted = true;
    setOutput("Loading the browser Python runtime\u2026", "loading");
    iframe.src = "/static/practice-sandbox.html";
    runnerLoadTimeout = setTimeout(() => {
      if (runnerReady) return;
      runnerStarted = false;
      queuedRun = false;
      runButton.disabled = false;
      iframe.src = "about:blank";
      setOutput("The Python runtime did not respond. Check that your browser allows background workers, then reload.", "error");
    }, 45e3);
  };
  const runChecks = () => {
    if (!problem) return;
    if (!runnerReady) {
      queuedRun = true;
      runButton.disabled = true;
      startRunner();
      return;
    }
    const runId = ++nextRunId;
    activeRunId = runId;
    runButton.disabled = true;
    setOutput("Running your code and optional local checks in the browser\u2026", "running");
    iframe.contentWindow.postMessage({
      type: "run",
      runId,
      code: `${currentSource()}

${customChecks.value}`
    }, "*");
    clearTimeout(runTimeout);
    runTimeout = setTimeout(() => {
      if (activeRunId !== runId) return;
      activeRunId = null;
      runButton.disabled = false;
      setOutput("Execution timed out. The browser worker was stopped; simplify the code and try again.", "error");
      runnerReady = false;
      runnerStarted = false;
      iframe.src = "about:blank";
    }, 1e4);
  };
  const submitCode = async () => {
    if (!problem || !await saveWorkspace()) return;
    submitButton.disabled = true;
    runButton.disabled = true;
    setOutput("Submitting to the isolated server judge\u2026", "running");
    try {
      const response = await fetch(submitUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": csrfToken
        },
        body: JSON.stringify({ code: currentSource() })
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.error || "Server judging is unavailable.");
      }
      let result = data;
      for (let attempt = 0; result.verdict === "PENDING" || result.verdict === "RUNNING"; attempt += 1) {
        if (attempt >= 60) throw new Error("The judge is taking longer than expected. Check your submission status shortly.");
        await new Promise((resolve) => setTimeout(resolve, 1e3));
        const statusResponse = await fetch(`/arena/api/submissions/${encodeURIComponent(data.submission_id)}`);
        result = await statusResponse.json();
        if (!statusResponse.ok) throw new Error(result.error || "Could not load submission status.");
      }
      const verdict = result.verdict || "INTERNAL_ERROR";
      setOutput(
        `${verdict.replaceAll("_", " ")} \xB7 ${result.tests_passed}/${result.total_tests} checks \xB7 ${result.execution_time_ms} ms`,
        verdict === "ACCEPTED" ? "done" : "error"
      );
      const status = document.getElementById("problem-status");
      if (verdict === "ACCEPTED") {
        status.textContent = "Demonstrated";
        status.dataset.verdict = verdict;
      }
    } catch (error) {
      setOutput(error.message || "Server judging is unavailable.", "error");
    } finally {
      submitButton.disabled = false;
      runButton.disabled = !runnerReady;
    }
  };
  const revealEditorial = async () => {
    if (!problem) return;
    if (!window.confirm("Reveal the worked solution? Try to save your own attempt first; the server only reveals this after an attempt exists.")) return;
    revealButton.disabled = true;
    try {
      const response = await fetch(editorialUrl);
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.error || "The worked solution is not available yet.");
      }
      editorialCode.textContent = data.solution_code || "(No reference code supplied.)";
      editorialProse.textContent = data.editorial || "";
      editorialPanel.classList.remove("hidden");
      editorialPanel.scrollIntoView({ block: "nearest" });
    } catch (error) {
      setOutput(error.message, "error");
    } finally {
      revealButton.disabled = false;
    }
  };
  runButton.addEventListener("click", () => {
    void saveWorkspace().then(runChecks);
  });
  submitButton.addEventListener("click", () => {
    void submitCode();
  });
  resetButton.addEventListener("click", () => {
    if (!problem) return;
    if (currentSource() !== problem.starter_code && !window.confirm("Discard your edits and restore the starter code?")) return;
    setEditorSource(problem.starter_code);
    queueSave();
    setOutput("Starter code restored.", "idle");
  });
  revealButton.addEventListener("click", () => {
    void revealEditorial();
  });
  document.querySelectorAll("[data-arena-hint]").forEach((button) => {
    button.addEventListener("click", async () => {
      button.disabled = true;
      hintOutput.textContent = "Preparing hint\u2026";
      try {
        const stage = Number(button.dataset.stage);
        const response = await fetch(
          `${hintUrl}?stage=${encodeURIComponent(stage)}`
        );
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.error || "Hint is unavailable.");
        hintOutput.textContent = data.hint;
      } catch (error) {
        hintOutput.textContent = error.message || "Hint is unavailable.";
      } finally {
        button.disabled = false;
      }
    });
  });
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") void saveWorkspace();
  });
  window.addEventListener("message", (event) => {
    if (event.source !== iframe.contentWindow || event.origin !== "null" || !event.data) return;
    if (event.data.type === "ready") {
      clearTimeout(runnerLoadTimeout);
      runnerReady = true;
      runButton.disabled = false;
      if (!queuedRun) setOutput("Python runtime ready. Run the public checks when you are ready.", "idle");
      if (queuedRun) {
        queuedRun = false;
        runChecks();
      }
      return;
    }
    if (event.data.type === "error" && event.data.runId == null) {
      clearTimeout(runnerLoadTimeout);
      runnerReady = false;
      queuedRun = false;
      runnerStarted = false;
      iframe.src = "about:blank";
      runButton.disabled = false;
      setOutput(event.data.text || "The Python runtime failed to load.", "error");
      return;
    }
    if (event.data.type === "run-started") {
      setOutput("Running public checks\u2026", "running");
      return;
    }
    if (event.data.runId !== activeRunId) return;
    if (event.data.type === "output") {
      output.textContent = `${output.textContent}${event.data.text}`.slice(0, 12e3);
    } else if (event.data.type === "done" || event.data.type === "error" || event.data.type === "timeout") {
      clearTimeout(runTimeout);
      activeRunId = null;
      runButton.disabled = false;
      setOutput(event.data.text, event.data.type === "done" ? "done" : "error");
    }
  });
  void loadProblem();
}
