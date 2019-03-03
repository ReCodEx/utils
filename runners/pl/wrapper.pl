% A Prolog wrapper for ReCodEx.
%
% Adam Dingle

% Print a single var/val pair, e.g. "X = [3, 6]".
showVar(Var, Val, N) :- (N > 1 -> write(', ') ; true), write(Var), write(' = '), write(Val).

% Print a set of var/val pairs, e.g. "X = [3, 6], Y = [2, 5]".
showVars(VarNames, Solution) :- length(VarNames, N), numlist(1, N, Nums),
                                maplist(showVar, VarNames, Solution, Nums), nl.

% Handle queries with no variables: just print 'true' or 'false'.
perform_query(Query, [], []) :-
    (call(Query) -> writeln('true') ; writeln('false')).

% Handle queries with variables.
perform_query(Query, Vars, VN) :-
    Vars = [_ | _],  % non-empty list
    maplist(arg(1), VN, VarNames),
    call(bagof(Vars, Query, Solutions)),  % find all solutions
    maplist(showVars(VarNames), Solutions).     % print them nicely

% Read a query from standard input, gather its solutions, and print them to standard output.
main :-
  prompt(_, ''),    % disable input prompt
  read_term(Query, [variables(Vars), variable_names(VN)]),
  perform_query(Query, Vars, VN),
  halt.
