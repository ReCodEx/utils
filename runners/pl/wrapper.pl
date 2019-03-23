% A Prolog wrapper for ReCodEx.
%
% Adam Dingle

% Print a single var/val pair, e.g. "X = [3, 6]".
recodex_showVar(Var, Val, N) :-
    (N > 1 -> write(', ') ; true), write(Var), write(' = '), write(Val).

% Print a set of var/val pairs, e.g. "X = [3, 6], Y = [2, 5]".
recodex_showVars(VarNames, Solution) :-
    length(VarNames, N), numlist(1, N, Nums),
    maplist(recodex_showVar, VarNames, Solution, Nums), nl.

% helper predicate for unzipping
eq(A = B, A, B).

% Handle queries with no variables: just print 'true' or 'false'.
recodex_perform_query(Query, []) :-
    (call(Query) -> writeln('true') ; writeln('false')).

% Handle queries with variables.
% We use findall to gather all solutions into a single list.  A query may contain
% anonymous variables ('_'), which will not appear in the list VN.  We use
% findall rather than bagof, because bagof will succeed once for each separate value
% of an anonymous variable.  findall succeeds only once and generates a single list.
recodex_perform_query(Query, VN) :-
    VN = [_ | _],                  % matches a non-empty list, e.g. ['X'=_8242, 'Y'=_8248]
    maplist(eq, VN, Names, Vars),  % unzip into Names = ['X', 'Y'], Vars = [_8242, _8248]
    (findall(Vars, Query, Solutions) -> true ; Solutions = []),  % find all solutions
    sort(Solutions, SortedSolutions),
    maplist(recodex_showVars(Names), SortedSolutions).     % print them nicely

% Read a query from standard input, gather its solutions, and print them to standard output.
recodex_main :-
  prompt(_, ''),    % disable input prompt
  read_term(Query, [variable_names(VN)]),
  recodex_perform_query(Query, VN),
  halt.
