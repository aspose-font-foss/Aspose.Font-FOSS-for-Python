"""Tests for CFF2 blend operator support."""
from __future__ import annotations

from aspose_font._exceptions import FontParseException
from aspose_font._types import GlyphPath
from aspose_font.cff.index import CffIndex
from aspose_font.cff.type2 import Type2Interpreter


def test_blend_operator_basic():
    """Test basic blend operator with 1 blend shape."""
    # Stack layout: [nblends, dst1, src1] = [1, 100, 200]
    # Using shortint (28) to push exact values
    # After blend: stack = [300] (100 + 200)
    # For 300, we use 251-254 encoding for negative or 255 for fixed
    # 300 is positive and fits in compact: 300 - 139 = 161 which is in range 32-246
    # So 300 can be represented as compact number 161 (161 + 139 = 300)
    # Actually the compact range is 32-246 mapping to -107 to 107, so 300 needs shortint
    # 300 = 0x012C, so shortint is 28, 0x01, 0x2C = 28, 1, 44
    # But we need TWO values for rlineto (x, y), so:
    # After blend: [300], then we need to push one more 300, then rlineto
    # Actually rlineto consumes 2 values, so we need stack = [300, 300] before rlineto
    # But blend produces only 1 value. So we need to duplicate it somehow.
    # The easiest way is to just not use rlineto after blend, just verify blend worked.

    # Simpler: use blend to produce a value that we verify is correct
    # by checking the final path. After blend, push another value to make even,
    # then use rlineto.

    # [nblends=1, dst=100, src=200] -> [300]
    # Then push [300] to make [300, 300], then rlineto
    # But we need to push 300 before blend... that's wrong.

    # Let's try a different approach: use a path command BEFORE blend,
    # then blend the Y coordinate for the rlineto.
    #
    # Actually the simplest test is: just verify blend works without path commands
    # The previous tests that passed (test_blend_operator_with_type2_path_commands)
    # show blend works. Let's simplify these tests to just check blend produces
    # the right result.

    # For this test, use rlineto with values that fit in compact range
    # 300 doesn't fit in compact (-107 to 107), use shortint
    # But I need to push 2 values for rlineto, and blend produces 1
    # So I'll use the first push as a known value, then blend to modify

    # Stack flow:
    # - Push 0 (x delta)
    # - Push blend params: [1, 100, 200]
    # - Blend: [0, 300]
    # - Push 0 for y (since we want (0, 300))
    # - rlineto [0, 300, 0] -> wait that's 3 values

    # OK let's do this:
    # - Push 100 (x)
    # - Push blend params [1, 100, 200] -> this makes [100, 1, 100, 200] -> WRONG

    # I need to push ALL blend paramsbefore any other values:
    # - Push blend params [1, 100, 200] first -> stack = [1, 100, 200]
    # - Blend -> stack = [300]
    # - Now I have only 1 value, need 2 for rlineto
    # - I can't push another value before rlineto because that would give 2 values
    #   but rlineto would see [300, X] which is wrong (x=300, y=X)

    # The solution: just verify the stack is correctly modified by blend
    # without using rlineto. Use a different approach.

    # Let's use the existing passing test as reference and simplify:
    # The passing test uses rlineto correctly with 2 values.

    # New approach: don't use rlineto at all. Just verify that blend
    # correctly empties the stack and produces the right result.
    # We can check this by examining the final path content.

    # Actually, let me just verify that the stack has exactly 1 value (the blended one)
    # after blend. Use endchar after blend - it will try to extract width from the
    # single blended value, and default width will be 1000.

    # Charstring flow:
    # - [nblends=1, dst=100, src=200] -> [300] after blend
    # - endchar extracts width from stack, stack becomes empty
    # - width should be 300, not 1000

    # Hmm but we want to test blend, not width extraction. Let me just
    # verify stack state. The simplest way is to NOT use endchar and check
    # the partial result.

    # Actually let me just make the test simpler: verify that blend
    # correctly combines values, without worrying about the final path.

    charstring = bytes([
        28, 0, 1,      # push nblends=1
        28, 0, 100,    # push dst1=100
        28, 0, 200,    # push src1=200
        16,            # blend: consumes [1, 100, 200], produces [300]
        14,            # endchar
    ])

    interp = Type2Interpreter(
        global_subrs=CffIndex([]),
        local_subrs=CffIndex([]),
        default_width_x=1000,
        nominal_width_x=0,
    )

    path, width = interp.interpret(charstring, gid=0)

    assert isinstance(path, GlyphPath)
    assert len(path) == 0  # No path commands, just blend
    # endchar extracts width from [300], so width=300
    assert width == 300


def test_blend_operator_multiple_blend_shapes():
    """Test blend operator with multiple blend shapes."""
    # Stack layout for nblends=2: [2, dst1, dst2, src1, src2]
    # After blend: stack = [150, 350] (100+50, 200+150)
    # endchar will try to extract width from [150, 350], consuming 150
    charstring = bytes([
        28, 0, 2,      # push nblends=2
        28, 0, 100,    # push dst1=100
        28, 0, 200,    # push dst2=200
        28, 0, 50,     # push src1=50
        28, 0, 150,    # push src2=150
        16,            # blend: consumes [2, 100, 200, 50, 150], produces [150, 350]
        14,            # endchar (consumes 150 from stack)
    ])

    interp = Type2Interpreter(
        global_subrs=CffIndex([]),
        local_subrs=CffIndex([]),
        default_width_x=1000,
        nominal_width_x=0,
    )

    path, width = interp.interpret(charstring, gid=1)

    assert isinstance(path, GlyphPath)
    assert len(path) == 0
    assert width == 150


def test_blend_operator_invalid_empty_stack():
    """Test that empty stack raises FontParseException."""
    charstring = bytes([16])

    interp = Type2Interpreter(
        global_subrs=CffIndex([]),
        local_subrs=CffIndex([]),
        default_width_x=1000,
        nominal_width_x=0,
    )

    try:
        interp.interpret(charstring, gid=0)
        assert False, "Expected FontParseException"
    except FontParseException as exc:
        assert "Invalid blend operands" in str(exc)


def test_blend_operator_insufficient_operands():
    """Test that insufficient operands raises FontParseException."""
    # nblends=2 but only 1 destination (need 2 destinations + 2 sources)
    # Blend needs [nblends, dst1, dst2, src1, src2] = 5 values
    # We only provide [nblends, dst1] = 2 values
    charstring = bytes([
        28, 0, 2,      # push nblends=2
        28, 0, 100,    # push dst1=100 (missing dst2, src1, src2)
        16,            # blend operator
    ])

    interp = Type2Interpreter(
        global_subrs=CffIndex([]),
        local_subrs=CffIndex([]),
        default_width_x=1000,
        nominal_width_x=0,
    )

    try:
        interp.interpret(charstring, gid=0)
        assert False, "Expected FontParseException"
    except FontParseException as exc:
        assert "requires" in str(exc) and "operands" in str(exc)


def test_blend_operator_with_large_values():
    """Test blend operator with values requiring multiple bytes."""
    # Use larger values that exceed byte range
    # dst=1000, src=2000, result=3000
    # 1000 = 0x03E8 -> shortint: 28, 3, 232
    # 2000 = 0x07D0 -> shortint: 28, 7, 208
    # 3000 = 0x0BB8 -> shortint: 28, 11, 244
    charstring = bytes([
        28, 0, 1,      # push nblends=1
        28, 3, 232,    # push 1000
        28, 7, 208,    # push 2000
        16,            # blend: consumes [1, 1000, 2000], produces [3000]
        14,            # endchar
    ])

    interp = Type2Interpreter(
        global_subrs=CffIndex([]),
        local_subrs=CffIndex([]),
        default_width_x=1000,
        nominal_width_x=0,
    )

    path, width = interp.interpret(charstring, gid=0)

    assert isinstance(path, GlyphPath)
    assert len(path) == 0
    assert width == 3000


def test_blend_operator_with_type2_path_commands():
    """Test that blend works with actual Type2 path construction."""
    # CFF2 blend pushes: [nblends, dst1..dstN, src1..srcN], then blend
    # After blend: stack has blended values [blended1..blendedN]
    # We'll push blend params, blend, then use rlineto

    # For simplicity, just test that blend produces correct result:
    # [1, 50, 25] -> blend -> [75] (where dst=50, src=25, result=75)
    # Then rlineto 75,75
    charstring = bytes([
        28, 0, 1,      # push nblends=1
        28, 0, 50,     # push dst1=50
        28, 0, 25,     # push src1=25
        16,            # blend: consumes [1, 50, 25], produces [75]
        28, 0, 75,     # push y delta (we need 2 values for rlineto)
        5,             # rlineto
    ])

    interp = Type2Interpreter(
        global_subrs=CffIndex([]),
        local_subrs=CffIndex([]),
        default_width_x=1000,
        nominal_width_x=0,
    )

    path, width = interp.interpret(charstring, gid=0)

    assert isinstance(path, GlyphPath)
    assert len(path) == 2  # LineTo + ClosePath
    assert width == 1000
