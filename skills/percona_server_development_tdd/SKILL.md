---
name: mysql-server-development
description: "Server code authoring. Use when touching server code, including comment-only and formatting."
---

# Development

Development is carried out in a docker container. There is no need for bubblewrap or socat.

# Doxygen formatting

Doxgen comments are formatted as follows:

/**
  Brief description in one sentence. Long. Description. May. Contain. Several.
  Sentences.

  @param[in]      myparam1 An input parameter
  @param[in, out] myparam2 A parameter that is both input and output
  @param[out]     myparam2 An output parameter

  @tparam mytemplate Description of template parameter

  @return Describes the nature of the return, does not repeat values, however "true if this, false if that" is OK.
*/

Lines break at 80 columns. Sentences start with a capital, except when the first word is an identifier, e.g. `true`.

# Terminology

Mysql has a legacy of abusing terminology with vague and overlapping meanings. Whenever we write new internal documentation and name things, we stick to the standard SQL syntax

| Legacy MySQL Term | SQL Standard Term |
|---|-|
| Key (referring to an index) | Index        |
| Keypart                     | Index column |

# Coding Style

The code is in the midst of a refactoring/modernization. When in doubt, opt for modern C++20 coding style. New code should follow the Google C++ coding style.

