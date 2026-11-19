"""SQL keyword dictionary used by the lexer."""

KEYWORDS = {
    keyword: keyword
    for keyword in (
        "SELECT","FROM","WHERE","AND","CREATE","TABLE","INDEX","INSERT","INTO","ON",
        "VALUES","UPDATE","SET","DELETE","BEGIN","TRANSACTION",
        "COMMIT","ROLLBACK","EXPLAIN","PRIMARY","KEY","NOT","NULL",
        "INT","INTEGER","FLOAT","REAL","TEXT","BOOL","BOOLEAN","USING","HASH","BTREE","TRUE","FALSE",
)
}
