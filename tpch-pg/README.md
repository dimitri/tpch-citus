# TPCH PostgreSQL Port

This is a port of the TPC-H test suite, written to support PostgreSQL:

  - queries have been fixed (misplaced semicolons).
  - direct loading support for PostgreSQL using the COPY protocol is added.
  - changes in the per-step data distribution are done.
  - code cleanup to compile without warning on current platforms.

See below for details.
  
## Direct Loading

The TPC-H tooling is meant to support direct loading for the target system
being tested, but only offers series of empty functions in `load_stub.c` to
that end.

The C code also misses some basic infrastructure to enable direct loading to
be implemented. That said, the PORTING.NOTES file explains quite clearly the
concept, so in this repository we have added the capability to direct load
using PostgreSQL COPY protocol.

Given how the TPC-H tools are written, a separate connection is opened for
each target table being loaded with `dbgen`.

## Implementation Notes

The CHILDREN and STEPs behaviour has been adapted so that each step only
references data from the same step, rather than data from anywhere else in
the whole dataset. That allows loading the data one step in parallel, all
with having the Primary Key and Foreign Key constraints installed.

The goal is to be able to go from SF=1 to SF=30000 with incremental loading,
and even to do some COPY based loading in parallel to the STREAM
benchmarking.
