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

% Handle queries with no variables: just print 'true' or 'false'.
recodex_perform_query(Query, [], []) :-
    (call(Query) -> writeln('true') ; writeln('false')).

% Handle queries with variables.
recodex_perform_query(Query, Vars, VN) :-
    Vars = [_ | _],  % non-empty list
    maplist(arg(1), VN, VarNames),
    (call(bagof(Vars, Query, Solutions)) -> true ; Solutions = []),  % find all solutions
    sort(Solutions, SortedSolutions),
    maplist(recodex_showVars(VarNames), SortedSolutions).     % print them nicely

% Read a query from standard input, gather its solutions, and print them to standard output.
recodex_main :-
  prompt(_, ''),    % disable input prompt
  read_term(Query, [variables(Vars), variable_names(VN)]),
  recodex_perform_query(Query, Vars, VN),
  halt.
