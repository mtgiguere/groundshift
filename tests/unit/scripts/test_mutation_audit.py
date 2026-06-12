from pathlib import Path

from scripts.mutation_audit import Mutation, apply_mutation, collect_mutations


def _write(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


class TestCollectMutations:
    def test_returns_list(self, tmp_path):
        src = _write(tmp_path, "m.py", "x = 1\n")
        assert isinstance(collect_mutations(src), list)

    def test_finds_less_than(self, tmp_path):
        src = _write(tmp_path, "m.py", "if x < 0:\n    pass\n")
        mutations = collect_mutations(src)
        assert any(m.description.startswith("<") for m in mutations)

    def test_finds_greater_than(self, tmp_path):
        src = _write(tmp_path, "m.py", "if x > 0:\n    pass\n")
        mutations = collect_mutations(src)
        assert any(m.description.startswith(">") for m in mutations)

    def test_finds_and_operator(self, tmp_path):
        src = _write(tmp_path, "m.py", "if a and b:\n    pass\n")
        mutations = collect_mutations(src)
        assert any("and" in m.description for m in mutations)

    def test_finds_or_operator(self, tmp_path):
        src = _write(tmp_path, "m.py", "if a or b:\n    pass\n")
        mutations = collect_mutations(src)
        assert any("or" in m.description for m in mutations)

    def test_no_mutations_in_plain_assignment(self, tmp_path):
        src = _write(tmp_path, "m.py", "x = 1\ny = 2\n")
        assert collect_mutations(src) == []

    def test_mutation_has_correct_file_path(self, tmp_path):
        src = _write(tmp_path, "m.py", "if x < 0:\n    pass\n")
        mutations = collect_mutations(src)
        assert mutations[0].file == src

    def test_mutation_has_correct_line_number(self, tmp_path):
        src = _write(tmp_path, "m.py", "x = 1\nif x < 0:\n    pass\n")
        mutations = collect_mutations(src)
        assert mutations[0].line == 2

    def test_mutation_original_contains_operator(self, tmp_path):
        src = _write(tmp_path, "m.py", "if x < 0:\n    pass\n")
        mutations = collect_mutations(src)
        lt_mut = next(m for m in mutations if m.description.startswith("<"))
        assert " < " in lt_mut.original

    def test_mutation_mutant_contains_flipped_operator(self, tmp_path):
        src = _write(tmp_path, "m.py", "if x < 0:\n    pass\n")
        mutations = collect_mutations(src)
        lt_mut = next(m for m in mutations if m.description.startswith("<"))
        assert " > " in lt_mut.mutant

    def test_skips_comment_lines(self, tmp_path):
        src = _write(tmp_path, "m.py", "# if x < 0: do something\nx = 1\n")
        assert collect_mutations(src) == []

    def test_skips_and_inside_docstring(self, tmp_path):
        src = _write(tmp_path, "m.py", 'def f():\n    """Do this and that."""\n    pass\n')
        assert collect_mutations(src) == []

    def test_skips_multiline_docstring_content(self, tmp_path):
        content = 'def f():\n    """First line.\n\n    Uses x and y.\n    """\n    pass\n'
        src = _write(tmp_path, "m.py", content)
        assert collect_mutations(src) == []

    def test_does_not_skip_and_after_docstring(self, tmp_path):
        content = 'def f():\n    """Docstring."""\n    if a and b:\n        pass\n'
        src = _write(tmp_path, "m.py", content)
        mutations = collect_mutations(src)
        assert any("and" in m.description for m in mutations)

    def test_multiple_operators_on_same_line(self, tmp_path):
        src = _write(tmp_path, "m.py", "if x < 0 and y > 1:\n    pass\n")
        mutations = collect_mutations(src)
        assert len(mutations) >= 2

    def test_mutation_is_mutation_dataclass(self, tmp_path):
        src = _write(tmp_path, "m.py", "if x < 0:\n    pass\n")
        mutations = collect_mutations(src)
        assert isinstance(mutations[0], Mutation)

    def test_finds_min_method(self, tmp_path):
        src = _write(tmp_path, "m.py", "v = arr.min()\n")
        mutations = collect_mutations(src)
        assert any(".min()" in m.description for m in mutations)

    def test_min_mutated_to_max(self, tmp_path):
        src = _write(tmp_path, "m.py", "v = arr.min()\n")
        mutations = collect_mutations(src)
        min_mut = next(m for m in mutations if ".min()" in m.description)
        assert ".max()" in min_mut.mutant

    def test_finds_max_method(self, tmp_path):
        src = _write(tmp_path, "m.py", "v = arr.max()\n")
        mutations = collect_mutations(src)
        assert any(".max()" in m.description for m in mutations)


class TestApplyMutation:
    def test_changes_target_line(self, tmp_path):
        src = _write(tmp_path, "m.py", "x = 1\nif x < 0:\n    pass\n")
        apply_mutation(src, line_no=2, mutated_line="if x > 0:")
        lines = src.read_text(encoding="utf-8").splitlines()
        assert lines[1] == "if x > 0:"

    def test_leaves_other_lines_unchanged(self, tmp_path):
        src = _write(tmp_path, "m.py", "x = 1\nif x < 0:\n    pass\n")
        apply_mutation(src, line_no=2, mutated_line="if x > 0:")
        lines = src.read_text(encoding="utf-8").splitlines()
        assert lines[0] == "x = 1"
        assert lines[2] == "    pass"

    def test_roundtrip_restore(self, tmp_path):
        content = "x = 1\nif x < 0:\n    pass\n"
        src = _write(tmp_path, "m.py", content)
        apply_mutation(src, line_no=2, mutated_line="if x > 0:")
        apply_mutation(src, line_no=2, mutated_line="if x < 0:")
        assert src.read_text(encoding="utf-8") == content

    def test_first_line_mutation(self, tmp_path):
        src = _write(tmp_path, "m.py", "if x < 0:\n    pass\n")
        apply_mutation(src, line_no=1, mutated_line="if x > 0:")
        lines = src.read_text(encoding="utf-8").splitlines()
        assert lines[0] == "if x > 0:"

    def test_last_line_mutation(self, tmp_path):
        src = _write(tmp_path, "m.py", "x = 1\nif x < 0:\n    pass\n")
        apply_mutation(src, line_no=3, mutated_line="    return")
        lines = src.read_text(encoding="utf-8").splitlines()
        assert lines[2] == "    return"
