## evidence_id

ev_7d7f306267d8de12b7402b25fadc68279eb42e0979877ae4badd17c1179d64af

## subject.name

libflutter.so

## subject.digest

| Key    | Value                                                            |
|--------|------------------------------------------------------------------|
| sha256 | 0c56c4a468224beb2336c7bacaee6d5885047a0075d613fe421871b4dceafdce |

## subject.format

elf

## subject.architecture

arm64

## subject.local_path

<scratch>/lib/arm64-v8a/libflutter.so

## provider

| Key     | Value                               |
|---------|-------------------------------------|
| id      | rea-workflow                        |
| name    | REA composed investigation workflow |
| version | 1                                   |

## predicate_type

rea.analysis

## operation

trace_feature

## parameters

| Key            | Value                     |
|----------------|---------------------------|
| query          | vkCreateAndroidSurfaceKHR |
| case_sensitive | false                     |

## raw_result

null

## normalized_result.query

vkCreateAndroidSurfaceKHR

## normalized_result.search_mode

literal

## normalized_result.matches

| type   | address  | value                     |
|--------|----------|---------------------------|
| string | 0x1cfc94 | vkCreateAndroidSurfaceKHR |

## normalized_result.references

| target_address | source_address | containing_procedure |
|----------------|----------------|----------------------|
| 0x1cfc94       | 0x814da0       | [object Object]      |

## normalized_result.truncated

false

## normalized_result.residual_unknowns



## confidence

derived

## authority

shipped-artifact

## environment

null

## limitations

Derived by an REA composed workflow.

## locations



## evidence_links



## analysis_profile.provider

| Key     | Value                               |
|---------|-------------------------------------|
| id      | rea-workflow                        |
| name    | REA composed investigation workflow |
| version | 1                                   |

## analysis_profile.parameters.upstream_analysis_profile.provider

| Key     | Value                                                                            |
|---------|----------------------------------------------------------------------------------|
| id      | hopper                                                                           |
| name    | Hopper Disassembler                                                              |
| version | launcher-sha256:dad6f886261fad0d4cdd01aee6fcf57439c60d7b5c54e62fc97f0180116690e0 |

## analysis_profile.parameters.upstream_analysis_profile.parameters.target_kind

executable

## analysis_profile.parameters.upstream_analysis_profile.parameters.target_format

elf

## analysis_profile.parameters.upstream_analysis_profile.parameters.architecture

arm64

## analysis_profile.parameters.upstream_analysis_profile.parameters.available_architectures

arm64

## analysis_profile.parameters.upstream_analysis_profile.parameters.loader

| Key              | Value                                                            |
|------------------|------------------------------------------------------------------|
| source           | derived                                                          |
| argument_count   | 3                                                                |
| arguments_sha256 | c3ff6b5a7f3b0c7cec7685924ab1532ea79a6b8921458239491a37b14c59040c |

## analysis_profile.parameters.upstream_analysis_profile.digest

b0ba568e9120019acb82cf039da601e25ec3824a56db4ff2cfaa67f412b1f337

## analysis_profile.digest

92b0eed0d44061eaeb493eb23559fafde4ac4ad19ca601cc6ec984f6fc6ef517
