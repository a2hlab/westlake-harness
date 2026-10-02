	.file	"scopedlocale_reduction.cpp"
	.text
	.globl	_Z12build_localePKc             // -- Begin function _Z12build_localePKc
	.p2align	2
	.type	_Z12build_localePKc,@function
_Z12build_localePKc:                    // @_Z12build_localePKc
	.cfi_startproc
// %bb.0:
	sub	sp, sp, #32
	.cfi_def_cfa_offset 32
	stp	x29, x30, [sp, #16]             // 16-byte Folded Spill
	add	x29, sp, #16
	.cfi_def_cfa w29, 16
	.cfi_offset w30, -8
	.cfi_offset w29, -16
	sub	x1, x29, #4
	bl	_Z14forLanguageTagPKcRi
	ldur	w8, [x29, #-4]
	cmp	w8, #0
	b.le	.LBB0_2
// %bb.1:
	mov	w0, wzr
	b	.LBB0_3
.LBB0_2:
	bl	_Z16use_valid_localev
	mov	w0, #1                          // =0x1
.LBB0_3:
	.cfi_def_cfa wsp, 32
	ldp	x29, x30, [sp, #16]             // 16-byte Folded Reload
	add	sp, sp, #32
	.cfi_def_cfa_offset 0
	.cfi_restore w30
	.cfi_restore w29
	ret
.Lfunc_end0:
	.size	_Z12build_localePKc, .Lfunc_end0-_Z12build_localePKc
	.cfi_endproc
                                        // -- End function
	.ident	"Homebrew clang version 22.1.8"
	.section	".note.GNU-stack","",@progbits
	.addrsig
