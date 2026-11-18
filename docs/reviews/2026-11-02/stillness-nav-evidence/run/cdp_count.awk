# Counts DEBUG=pw:protocol messages between the SNL-MARK start/end lines nav-sets.spec.ts writes (flag cdpcount),
# and drops the protocol lines themselves (they are large). Everything else passes through.
/SNL-MARK start/ { inwin = 1; n = 0; send = 0; recv = 0; print; next }
/SNL-MARK end/   { printf "CDPCOUNT\t%s\ttotal=%d\tsend=%d\trecv=%d\n", $3, n, send, recv; inwin = 0; print; next }
/pw:protocol/    { all++; if (inwin) { n++; if ($0 ~ /SEND/) send++; else if ($0 ~ /RECV/) recv++ } ; next }
{ print }
END { printf "CDPCOUNT\tprotocol lines in the whole batch\t%d\n", all }
