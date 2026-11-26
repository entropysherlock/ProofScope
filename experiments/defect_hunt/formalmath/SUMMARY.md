# FormalMATH defect hunt — 5560 statements checked

**Controls: PASS** — ctrl_false_real: expected FALSE, certified ['FALSE']; ctrl_false_int: expected FALSE, certified ['FALSE']; ctrl_vacuous: expected VACUOUS, certified ['VACUOUS']; ctrl_true: expected None, certified []

Data `SphereLab/FormalMATH-All` · Lean 4.34.1 · Mathlib `d13f23b` · engine `proofscope/defect_hunt.py`

| Outcome | Count |
|---|---:|
| CANDIDATE | 111 |
| COMPILE_FAIL | 74 |
| NO_DEFECT_FOUND | 5325 |
| SEARCH_INCOMPLETE | 4 |
| SKIP_NO_THEOREM | 38 |
| SKIP_PLACEHOLDER | 1 |
| SKIP_UNIVERSE_POLY | 7 |

**Certified findings: 111** (each re-proved in a clean module, standard axioms only, leanchecker replay).

## fm_omni_theorem_2926 — FALSE
- certificate: `¬ (type_of% @omni_theorem_2926)`
- proof: `decide`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: What is the smallest integer that can be placed in the box so that $\frac{1}{2} < \frac{\square}{9}$?
 Prove that the answer is: 5

## fm_olymid-ref-base_2552 — FALSE
- certificate: `¬ (type_of% @olymid_ref_base_2552)`
- proof: `(intro h; refine absurd (@h ((1) : Nat) ((2) : Nat) ?_ ?_ ?_) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Soit $m, n$ des entiers positifs tels que $\operatorname{pgcd}(m, n)=1$, où $a \wedge b$ désigne le plus grand diviseur commun de $a$ et $b$. Quelle(s) valeur(s) peut prendre

$$
\left(2^{m}-2^{n} \wedge 2^{m^{2}+m n+n^{2}}-1\right) ?
$$
 Prove that the answer is: 1 \text{ et } 7

## fm_theorem_proving_zh_blue_988 — FALSE
- certificate: `¬ (type_of% @algebra_33567)`
- proof: `(intro h; refine absurd (@h ((0) : Real) ((-1) : Real) ((-1) : Real) ?_) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: real/rational witness — outside the prior audit's decide-over-integers counterexample search
- autobound: None
- informal: Given that \(xy + yz+zx = 1\), prove that:

\[x(1 - y)(1 - z^{2})+y(1 - z)(1 - x^{2})+z(1 - x^{2})(1 - y^{2})=4xyz\]

## fm_aime_all_1997_3 — FALSE
- certificate: `¬ (type_of% @aime_all_1997_3)`
- proof: `(intro h; refine absurd (@h ((0) : Nat) ((0) : Nat) ?_ ?_ ?_) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Sarah intended to multiply a two-digit number and a three-digit number, but she left out the multiplication sign and simply placed the two-digit number to the left of the three-digit number, thereby forming a five-digit number.  This number is exactly nine times the product Sarah should have obtained.  What is the sum of the two-digit number and the three-digit number? 
 Prove that the answer is: 126

## fm_olymid-ref-base_3929 — FALSE
- certificate: `¬ (type_of% @olymid_ref_base_3929)`
- proof: `decide`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: What is the smallest integer greater than 10 such that the sum of the digits in its base 17 representation is equal to the sum of the digits in its base 10 representation?
 Prove that the answer is: 153

## fm_omni_theorem_4152 — FALSE
- certificate: `¬ (type_of% @omni_theorem_4152)`
- proof: `(intro h; refine absurd (@h ((0) : Nat)) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Find the largest possible integer $k$, such that the following statement is true:  
Let $2009$ arbitrary non-degenerated triangles be given. In every triangle the three sides are coloured, such that one is blue, one is red and one is white. Now, for every colour separately, let us sort the lengths of the sides. We obtain
\[ \left. \begin{array}{rcl}
 & b_1 \leq b_2\leq\ldots\leq b_{2009} & \textrm{the lengths of the blue sides }\\
 & r_1 \leq r_2\leq\ldots\leq r_{2009} & \textrm{the lengths of t

## fm_omni_theorem_4006 — FALSE
- certificate: `¬ (type_of% @omni_theorem_4006)`
- proof: `(intro h; refine absurd (@h ((0) : Nat)) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Let $S(n)$ be the sum of the digits of the positive integer $n$. Find all $n$ such that $S(n)(S(n)-1)=n-1$.
 Prove that the answer is: $n=\{1,13,43,91,157\}$

## fm_olymid-ref-base_1698 — FALSE
- certificate: `¬ (type_of% @olymid_ref_base_1698)`
- proof: `(intro h; refine absurd (@h ((0) : Nat)) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Vind alle positieve gehele getallen $n$ waarvoor er $n$ verschillende natuurlijke getallen $a_{1}, a_{2}, \ldots, a_{n}$ bestaan, geen van alle groter dan $n^{2}$, zo dat de som

$$
\frac{1}{a_{1}}+\frac{1}{a_{2}}+\cdots+\frac{1}{a_{n}}=1 .
$$
 Prove that the answer is: not found

## fm_omni_theorem_3699 — FALSE
- certificate: `¬ (type_of% @omni_theorem_3699)`
- proof: `decide`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Determine the smallest positive integer $A$ with an odd number of digits and this property, that both $A$ and the number $B$ created by removing the middle digit of the number $A$ are divisible by $2018$.
 Prove that the answer is: 100902018

## fm_olymid-ref-base_701 — FALSE
- certificate: `¬ (type_of% @olymid_ref_base_701)`
- proof: `(intro h; refine absurd (@h ((1) : Nat) ((2) : Nat) ?_) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Let $m$ and $n$ be relatively prime positive integers. Determine all possible values of

$$
\operatorname{gcd}\left(2^{m}-2^{n}, 2^{m^{2}+m n+n^{2}}-1\right) .
$$

Answer: 1 and 7 .
 Prove that the answer is: 1 \text{ and } 7

## fm_DEMIMathAnalysis_55 — FALSE
- certificate: `¬ (type_of% @DEMIMathAnalysis_55)`
- proof: `(intro h; refine absurd (@h ((0) : Real)) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: real/rational witness — outside the prior audit's decide-over-integers counterexample search
- autobound: Unknown identifier `EulerGamma`

Note: It is not possible to treat `EulerGamma` as an implicitly bound variable here because the `autoImplicit` option is set to `false`.
- informal: Show that
\[
\frac{7}{12} - \gamma = \int_{0}^\infty \frac{\{x\}^2 (1 - \{x\})^2}{(1 + x)^5} \, dx,
\]
where \( \gamma \) is Euler's constant and \( \{x\} \) denotes the fractional part of \( x \).

## fm_theorem_proving_zh_blue_1245 — FALSE
- certificate: `¬ (type_of% @algebra_68645)`
- proof: `(intro h; refine absurd (@h ((0) : Real) ((0) : Real) ((1) : Real)) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: real/rational witness — outside the prior audit's decide-over-integers counterexample search
- autobound: None
- informal: Proof: In \(\triangle ABC\), we need to prove that
\[
\sum_{cyc}a^{3}-2\sum_{cyc}a^{2}(b + c)+9abc\leqslant0.
\]

## fm_olymid-ref-base_3668 — FALSE
- certificate: `¬ (type_of% @olymid_ref_base_3668)`
- proof: `(intro h; refine absurd (@h ((0) : Real)) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: real/rational witness — outside the prior audit's decide-over-integers counterexample search
- autobound: Unknown identifier `I`

Note: It is not possible to treat `I` as an implicitly bound variable here because the `autoImplicit` option is set to `false`.
- informal: Simplify
$$
2 \cos ^{2}(\ln (2009) i)+i \sin (\ln (4036081) i)
$$
 Prove that the answer is: \frac{4036082}{4036081}

## fm_olymid-ref-base_4753 — FALSE
- certificate: `¬ (type_of% @olymid_ref_base_4753)`
- proof: `decide`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Find the smallest positive integer $b$ such that $1111_{b}$ ( 1111 in base $b$ ) is a perfect square. If no such $b$ exists, write "No solution".
 Prove that the answer is: 7

## fm_olymid-ref-base_9813 — FALSE
- certificate: `¬ (type_of% @olymid_ref_base_9813)`
- proof: `(intro h; refine absurd (@h ((0) : Nat)) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: 15. (MEX 2) Determine for which positive integers $k$ the set  $$ X=\{1990,1990+1,1990+2, \ldots, 1990+k\} $$  can be partitioned into two disjoint subsets $A$ and $B$ such that the sum of the elements of $A$ is equal to the sum of the elements of $B$.
 Prove that the answer is: k=4r+3, r \geq 0, \text{ and } k=4r, r \geq 23

## fm_theorem_proving_zh_blue_1454 — FALSE
- certificate: `¬ (type_of% @algebra_379525)`
- proof: `(intro h; refine absurd (@h ((1) : Nat) ?_) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Proof: For any \(n\in\mathbf{N}^*\), we need to prove that
\[
\frac{1}{1\times2}+\frac{1}{2\times3}+\cdots+\frac{1}{n(n + 1)}=1-\frac{1}{n + 1}\quad (\text{Equation }1)
\]

First, we decompose the general term \(\frac{1}{k(k + 1)}\) using partial fraction decomposition.

We know that \(\frac{1}{k(k + 1)}=\frac{1}{k}-\frac{1}{k + 1}\)

Now, consider the left side of the equation:

\[
\begin{align*}
L&=\frac{1}{1\times2}+\frac{1}{2\times3}+\cdots+\frac{1}{n(n + 1)}\\
&=\left(1-\frac{1}{2}\right)+\

## fm_omni_theorem_4276 — FALSE
- certificate: `¬ (type_of% @omni_theorem_4276)`
- proof: `(intro h; refine absurd (@h ((2) : Nat) ((2) : Nat) ?_ ?_) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Solve in prime numbers the equation $x^y - y^x = xy^2 - 19$.
 Prove that the answer is: (2, 3)(2, 7)

## fm_u-math_72 — FALSE
- certificate: `¬ (type_of% @u_math_72)`
- proof: `(norm_num; done)`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: An epidemiological study of the spread of a certain influenza strain that hit a small school population found that the total number of students, $P$, who contracted the flu $t$ days after it broke out is given by the model $P = t^2 - 14t + 200$, where $1 \leq t \leq 6$. Find the day that 160 students had the flu. Recall that the restriction on $t$ is at most 6.
 Prove that the answer is: The final answer: $4$

## fm_u-math_462 — FALSE
- certificate: `¬ (type_of% @u_math_462)`
- proof: `(intro h; refine absurd (@h ((3) : Rat) ?_) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: real/rational witness — outside the prior audit's decide-over-integers counterexample search
- autobound: None
- informal: Divide the rational expressions:
$$
\frac{ q^2-9 }{ q^2+6 \cdot q+9 } \div \frac{ q^2-2 \cdot q-3 }{ q^2+2 \cdot q-3 }
$$
 Prove that the answer is: The final answer: $\frac{q-1}{q+1}$

## fm_olymid-ref-base_10079 — FALSE
- certificate: `¬ (type_of% @olymid_ref_base)`
- proof: `(intro h; refine absurd (@h ((0) : Nat)) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: 14. N1 (JAP) Determine all positive integers $n \geq 2$ that satisfy the following condition: For all integers $a, b$ relatively prime to $n$,  $$ a \equiv b(\bmod n) \quad \text { if and only if } \quad a b \equiv 1(\bmod n) $$
 Prove that the answer is: n \mid 24

## fm_olymid-ref-base_3251 — FALSE
- certificate: `¬ (type_of% @olymid_ref_base_3251)`
- proof: `(intro h; refine absurd (@h ((5) : Nat) ?_) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Prove that for every integer $n$ greater than 1 ,

$$
\sigma(n) \phi(n) \leq n^{2}-1
$$

When does equality hold?

## fm_quantitative_reasoning_zh_blue_379 — FALSE
- certificate: `¬ (type_of% @quantitative_reasoning_zh_blue_379)`
- proof: `(intro h; refine absurd (@h ((0) : Nat)) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Find all positive integers \(n\) such that there exist non - zero integers \(x_1,x_2,\cdots,x_n,y\) satisfying
\[
\begin{cases}
x_1+\cdots +x_n = 0\\
x_1^2+\cdots +x_n^2=ny^2
\end{cases}
\]

Proof: Obviously \(n\neq1\).

When \(n = 2k\) (\(k\in\mathbf{N}^*\)), let \(x_{2i - 1}=1\), \(x_{2i}=-1\), \(i = 1,2,\cdots,k\) and \(y = 1\), then the conditions are satisfied.

When \(n=3 + 2k\) (\(k\in\mathbf{N}^*\)), let \(y = 2\), \(x_1 = 4\), \(x_2=x_3=x_4=x_5=-1\),
\[x_{2i}=2\], \[x_{2i + 1}=-2\], \(i

## fm_omni_theorem_1615 — VACUOUS
- certificate: `vacuous_of% @omni_theorem_1615`
- proof: `(intros; norm_num at *; done)`
- novelty: contradiction found by `(intros; norm_num at *; done)` — prior audit used omega/grind
- autobound: None
- informal: Let $z$ be a non-real complex number with $z^{23}=1$. Compute $$ \sum_{k=0}^{22} \frac{1}{1+z^{k}+z^{2 k}} $$
 Prove that the answer is: 46 / 3

## fm_omni_theorem_1576 — FALSE
- certificate: `¬ (type_of% @omni_theorem_1576)`
- proof: `(intro h; refine absurd (@h ((0) : Nat)) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Determine all positive integers $n$ for which the equation $$x^{n}+(2+x)^{n}+(2-x)^{n}=0$$ has an integer as a solution.
 Prove that the answer is: n=1

## fm_theorem_proving_zh_blue_1269 — FALSE
- certificate: `¬ (type_of% @algebra_418898)`
- proof: `(intro h; refine absurd (@h ((1) : Real) ((1) : Real) ((1) : Real) ?_ ?_ ?_ ?_) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: real/rational witness — outside the prior audit's decide-over-integers counterexample search
- autobound: None
- informal: Let \(a,b,c\in\mathbf{R}^{+}\) and \(abc = 1\). Prove that:
(1) \(\frac{1}{1 + 2a}+\frac{1}{1 + 2b}+\frac{1}{1 + 2c}\geqslant1\);
(2) \(\frac{1}{1+\frac{1}{a + b}}+\frac{1}{1 + b + c}+\frac{1}{1 + c + a}\leqslant1\).

## fm_olymid-ref-base_506 — FALSE
- certificate: `¬ (type_of% @olymid_ref_base_506)`
- proof: `(intro h; refine absurd (@h ((1) : Nat) ?_ ?_) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Let $n$ be a positive integer such that the sum of all the positive divisors of $n$ (except $n$ ) plus the number of these divisors is equal to $n$. Prove that $n=2 m^{2}$ for some integer $m$.

## fm_aime_all_2007_II_4 — VACUOUS
- certificate: `vacuous_of% @aime_all_2007_II_4`
- proof: `(intros; linarith)`
- novelty: contradiction found by `(intros; linarith)` — prior audit used omega/grind
- autobound: None
- informal: The workers in a factory produce widgets and whoosits. For each product, production time is constant and identical for all workers, but not necessarily equal for the two products. In one hour, $100$ workers can produce $300$ widgets and $200$ whoosits. In two hours, $60$ workers can produce $240$ widgets and $300$ whoosits. In three hours, $50$ workers can produce $150$ widgets and $m$ whoosits. Find $m$ .
 Prove that the answer is: 450

## fm_olymid-ref-base_7189 — FALSE
- certificate: `¬ (type_of% @olymid_ref_base_7189)`
- proof: `(intro h; norm_num at h; done)`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: How many digits are in the base two representation of 10 ! (factorial)?
 Prove that the answer is: 21

## fm_u-math_364 — FALSE
- certificate: `¬ (type_of% @u_math_364)`
- proof: `(intro h; refine absurd (@h ((1) : Int) ((0) : Real) ?_ ((0) : Nat)) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: real/rational witness — outside the prior audit's decide-over-integers counterexample search
- autobound: None
- informal: Given $k$ as an integer and $a \ne \pi \cdot k$, evaluate $P=\cos(a) \cdot \cos(2 \cdot a) \cdot \cos(4 \cdot a) \ldots \cos\left(2^n \cdot a\right)$.
 Prove that the answer is: The final answer: $P=\frac{1}{2^{n+1}}\cdot\frac{\sin\left(2^{n+1}\cdot a\right)}{\sin(a)}$

## fm_omni_theorem_3473 — FALSE
- certificate: `¬ (type_of% @omni_theorem_3473)`
- proof: `(intro h; norm_num at h; done)`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Which of the following is equal to $110 \%$ of 500?
 Prove that the answer is: 550

## fm_olymid-ref-base_9952 — VACUOUS
- certificate: `vacuous_of% @olymid_ref_base_9952`
- proof: `(intros; simp_all; done)`
- novelty: contradiction found by omega/simp — may overlap the prior audit
- autobound: None
- informal: 25. S3 (POL) For an integer $x \geq 1$, let $p(x)$ be the least prime that does not divide $x$, and define $q(x)$ to be the product of all primes less than $p(x)$. In particular, $p(1)=2$. For $x$ such that $p(x)=2$, define $q(x)=1$. Consider the sequence $x_{0}, x_{1}, x_{2}, \ldots$ defined by $x_{0}=1$ and  $$ x_{n+1}=\frac{x_{n} p\left(x_{n}\right)}{q\left(x_{n}\right)} $$  for $n \geq 0$. Find all $n$ such that $x_{n}=1995$.
 Prove that the answer is: 142

## fm_u-math_413 — FALSE
- certificate: `¬ (type_of% @u_math_413)`
- proof: `(intro h; refine absurd (@h ((0) : Nat)) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: Unknown identifier `X`

Note: It is not possible to treat `X` as an implicitly bound variable here because the `autoImplicit` option is set to `false`.
- informal: Divide rational expressions and simplify it:

$$
\frac{ x^2-1 }{ 2 } \div \frac{ x-1 }{ 5 }
$$
 Prove that the answer is: The final answer: $\frac{5}{2}\cdot x+\frac{5}{2}$

## fm_omni_theorem_1435 — FALSE
- certificate: `¬ (type_of% @omni_theorem_1435)`
- proof: `(intro h; refine absurd (@h ((1) : Nat) ?_) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Determine all positive integers $n$ for which $\frac{n^{2}+1}{[\sqrt{n}]^{2}+2}$ is an integer. Here $[r]$ denotes the greatest integer less than or equal to $r$.
 Prove that the answer is: No positive integers n satisfy the condition.

## fm_u-math_684 — FALSE
- certificate: `¬ (type_of% @u_math_684)`
- proof: `(norm_num; done)`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: An epidemiological study of the spread of a certain influenza strain that hit a small school population found that the total number of students, $P$, who contracted the flu $t$ days after it broke out is given by the model $P = t^2 - 12t + 180$, where $1 \leq t \leq 6$. Find the day that $160$ students had the flu. Recall that the restriction on $t$ is at most $6$.
 Prove that the answer is: The final answer: $2$

## fm_theorem_proving_zh_blue_1183 — FALSE
- certificate: `¬ (type_of% @algebra_479695)`
- proof: `(intro h; refine absurd (@h ((1) : Nat) ?_) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: For each positive integer \(n\), prove that:
\[
\sum_{j = 1}^{n}\frac{2j + 1}{j^{2}}>n\left[(n + 1)^{\frac{2}{n}}-1\right].
\]

## fm_theorem_proving_zh_blue_896 — FALSE
- certificate: `¬ (type_of% @theorem_proving_zh_blue_896)`
- proof: `(intro h; refine absurd (@h ((0) : Real)) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: real/rational witness — outside the prior audit's decide-over-integers counterexample search
- autobound: None
- informal: Proof: Prove that \(\sin^{2}x+\frac{4}{\sin^{2}x}\geqslant5\).

## fm_aime_all_2020_II_5 — FALSE
- certificate: `¬ (type_of% @aime_all_2020_II_5)`
- proof: `decide`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: For each positive integer $n$ , let $f(n)$ be the sum of the digits in the base-four representation of $n$ and let $g(n)$ be the sum of the digits in the base-eight representation of $f(n)$ . For example, $f(2020) = f(133210_{\text{4}}) = 10 = 12_{\text{8}}$ , and $g(2020) = \text{the digit sum of }12_{\text{8}} = 3$ . Let $N$ be the least value of $n$ such that the base-sixteen representation of $g(n)$ cannot be expressed using only the digits $0$ through $9$ . Find the remainder when $N$ is di

## fm_olymid-ref-base_10839 — FALSE
- certificate: `¬ (type_of% @olymid_ref_base_10839)`
- proof: `(intro h; refine absurd (@h ((0) : Nat)) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Find all prime numbers $p$ such that

$$
(x+y)^{19}-x^{19}-y^{19}
$$

is a multiple of $p$ for any positive integers $x, y$.
 Prove that the answer is: 2, 3, 7, 19

## fm_olymid-ref-base_5439 — FALSE
- certificate: `¬ (type_of% @olymid_ref_base_5439)`
- proof: `(intro h; refine absurd (@h ((0) : Nat)) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Find all positive integers $n$ for which there do not exist $n$ consecutive composite positive integers less than $n$ !.
 Prove that the answer is: 1,2,3,4

## fm_omni_theorem_4351 — FALSE
- certificate: `¬ (type_of% @omni_theorem_4351)`
- proof: `(intro h; refine absurd (@h ((0) : Real) ((0) : Real)) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: real/rational witness — outside the prior audit's decide-over-integers counterexample search
- autobound: None
- informal: Find $x$ such that trigonometric 
\[\frac{\sin 3x \cos (60^\circ -x)+1}{\sin(60^\circ - 7x) - \cos(30^\circ + x) + m}=0\]
where $m$ is a fixed real number.
 Prove that the answer is: $\text{  no solution }$

## fm_theorem_proving_zh_blue_1176 — FALSE
- certificate: `¬ (type_of% @algebra_48694)`
- proof: `(intro h; norm_num at h; done)`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Prove that \(\left(1 - \frac{1}{365}\right)\left(1-\frac{2}{365}\right)\cdots\left(1-\frac{25}{365}\right)<\frac{1}{2}\).

## fm_u-math_382 — FALSE
- certificate: `¬ (type_of% @u_math_382)`
- proof: `(intro h; refine absurd (@h ((0) : Int)) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: Unknown identifier `X`

Note: It is not possible to treat `X` as an implicitly bound variable here because the `autoImplicit` option is set to `false`.
- informal: Use synthetic division to find the quotient and remainder. Ensure the equation is in the form required by synthetic division:

$$
\frac{ 4 \cdot x^3-12 \cdot x^2-5 \cdot x-1 }{ 2 \cdot x+1 }
$$

Hint: divide the dividend and divisor by the coefficient of the linear term in the divisor. Solve on a paper, if it is more convenient for you.
 Prove that the answer is: Quotient: $2\cdot x^2-7\cdot x+1$ Remainder: $-2$

## fm_olymid-ref-base_10819 — FALSE
- certificate: `¬ (type_of% @olymid)`
- proof: `(intro h; refine absurd (@h ((0) : Nat) ((0) : Nat) ((0) : Nat)) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Find all triples $(p, q, r)$ of prime numbers such that all of the following numbers are integers

$$
\frac{p^{2}+2 q}{q+r}, \quad \frac{q^{2}+9 r}{r+p}, \quad \frac{r^{2}+3 p}{p+q}
$$
 Prove that the answer is: (2,3,7)

## fm_theorem_proving_zh_blue_1022 — FALSE
- certificate: `¬ (type_of% @algebra_58892)`
- proof: `(intro h; refine absurd (@h ((0) : Real) ((1) : Real) ((-1) : Real)) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: real/rational witness — outside the prior audit's decide-over-integers counterexample search
- autobound: None
- informal: Given that \(x,y,z\in\mathbf{R}\), prove that:
\[
\frac{x - y}{1+xy}+\frac{y - z}{1+yz}+\frac{z - x}{1+xz}=\frac{(x - y)(y - z)(z - x)}{(1+xy)(1+yz)(1+zx)}
\]

## fm_olymid-ref-base_2558 — FALSE
- certificate: `¬ (type_of% @olymid_ref_base_2558)`
- proof: `(intro h; refine absurd (@h ((1) : Nat) ((2) : Nat) ?_ ?_) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Soit $m$ et $n$ des entiers naturels non nuls. Prouver que

$$
\frac{(m+n)!}{(m+n)^{m+n}}<\frac{m!}{m^{m}} \frac{n!}{n^{n}}
$$

## fm_olymid-ref-base_10794 — FALSE
- certificate: `¬ (type_of% @olymid_ref_base_10794)`
- proof: `(intro h; refine absurd (@h ((0) : Nat)) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Find all positive integers $n$ such that there exists a prime number $p$, such that

$$
p^{n}-(p-1)^{n}
$$

is a power of 3 .

Note. A power of 3 is a number of the form $3^{a}$ where $a$ is a positive integer.
 Prove that the answer is: n=2

## fm_omni_theorem_1527 — FALSE
- certificate: `¬ (type_of% @omni_theorem_1527)`
- proof: `(intro h; refine absurd (@h ((0) : Nat)) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Find all positive integers $n$ such that for any integer $k$ there exists an integer $a$ for which $a^{3}+a-k$ is divisible by $n$.
 Prove that the answer is: All integers $n=3^{b}$, where $b$ is a nonnegative integer.

## fm_olymid-ref-base_6296 — FALSE
- certificate: `¬ (type_of% @olymid_ref_base_6296)`
- proof: `(intro h; norm_num at h; done)`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Is

$$
\prod_{k=0}^{\infty}\left(1-\frac{1}{2022^{k!}}\right)
$$

rational?
 Prove that the answer is: No

## fm_theorem_proving_zh_blue_81 — FALSE
- certificate: `¬ (type_of% @theorem_proving_zh_blue_81)`
- proof: `(intro h; refine absurd (@h ((0) : Nat)) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Try to determine all positive integers \(n\) such that the set \(\{1, 2,\cdots, n\}\) can be partitioned into 5 non - overlapping subsets, and the sum of the elements in each subset is equal. 

## fm_theorem_proving_zh_blue_679 — FALSE
- certificate: `¬ (type_of% @theorem_proving_zh_blue_679)`
- proof: `(intro h; refine absurd (@h ((0) : Nat)) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: For what positive integers \(n\) can the set \(\{1, 2,\cdots, n\}\) be partitioned into 5 non - overlapping subsets such that the sum of the elements in each subset is equal? 

## fm_omni_theorem_2887 — VACUOUS
- certificate: `vacuous_of% @omni_theorem_2887`
- proof: `(intros; omega)`
- novelty: contradiction found by omega/simp — may overlap the prior audit
- autobound: None
- informal: Chris received a mark of $50 \%$ on a recent test. Chris answered 13 of the first 20 questions correctly. Chris also answered $25 \%$ of the remaining questions on the test correctly. If each question on the test was worth one mark, how many questions in total were on the test?
 Prove that the answer is: 32

## fm_olymid-ref-base_7209 — FALSE
- certificate: `¬ (type_of% @olymid_ref_base_7209)`
- proof: `(intro h; refine absurd (@h ((1) : Real) ((1) : Real) ((1) : Real) ?_ ?_ ?_ ?_) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: real/rational witness — outside the prior audit's decide-over-integers counterexample search
- autobound: None
- informal: Given that $a, b, c$ are positive real numbers and $\log _{a} b+\log _{b} c+\log _{c} a=0$, find the value of $\left(\log _{a} b\right)^{3}+\left(\log _{b} c\right)^{3}+\left(\log _{c} a\right)^{3}$.
 Prove that the answer is: 3

## fm_olymid-ref-base_9798 — FALSE
- certificate: `¬ (type_of% @olymid_ref_base_9798)`
- proof: `(intro h; refine absurd (@h ((0) : Nat)) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: 30. (SWE 2) ${ }^{\mathrm{IMO} 5}$ For which positive integers $n$ does there exist a positive integer $N$ such that none of the integers $1+N, 2+N, \ldots, n+N$ is the power of a prime number?

## fm_olymid-ref-base_2721 — FALSE
- certificate: `¬ (type_of% @olymid_ref_base_2721)`
- proof: `(intro h; refine absurd (@h ((1) : Nat) ((2) : Nat) ?_ ?_) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Trouver tous les entiers $m \geqslant 1$ et $n \geqslant 1$ tels que $\frac{5^{m}+2^{n+1}}{5^{m}-2^{n+1}}$ soit le carré d'un entier.
 Prove that the answer is: m=n=1

## fm_u-math_64 — FALSE
- certificate: `¬ (type_of% @u_math_64)`
- proof: `(intro h; refine absurd (@h ((1/2) : Real) ((0) : Real) ?_) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: real/rational witness — outside the prior audit's decide-over-integers counterexample search
- autobound: None
- informal: Find all values of $t$ that satisfy the following equation:
$$
\log_{a}(t) + \log_{2 \cdot a}(t) = \frac{ \ln\left(2 \cdot a^2\right) }{ \ln(2 \cdot a) }
$$
for $a > 0$ and $a \ne 1$.
 Prove that the answer is: $t$ = $a$

## fm_olymid-ref-base_918 — FALSE
- certificate: `¬ (type_of% @olymid_ref_base_918)`
- proof: `(intro h; refine absurd (@h ((0) : Real) ?_) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: real/rational witness — outside the prior audit's decide-over-integers counterexample search
- autobound: None
- informal: Let $[x]$ be the integer part of a number $x$, and $\{x\}=x-[x]$. Solve the equation

$$
[x] \cdot\{x\}=1991 x .
$$
 Prove that the answer is: -\frac{1}{1992}

## fm_theorem_proving_zh_blue_1350 — FALSE
- certificate: `¬ (type_of% @inequalities_8712)`
- proof: `(intro h; refine absurd (@h ((0) : Real) ((1) : Real) ((1) : Real) ?_ ?_ ?_) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: real/rational witness — outside the prior audit's decide-over-integers counterexample search
- autobound: None
- informal: Let \(x,y,z\geqslant0\). Prove that:
\[
x(y + z - x)^{2}+y(z + x - y)^{2}+z(x + y - z)^{2}\geqslant3xyz.
\]
And determine the conditions for the equality to hold.

## fm_omni_theorem_3873 — FALSE
- certificate: `¬ (type_of% @omni_theorem_3873)`
- proof: `(intro h; refine absurd (@h ((0) : Nat)) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Find all positive integers $n$ such that: 
\[ \dfrac{n^3+3}{n^2+7} \]
is a positive integer.
 Prove that the answer is: 2 \text{ and } 5

## fm_omni_theorem_4271 — FALSE
- certificate: `¬ (type_of% @omni_theorem_4271)`
- proof: `(intro h; refine absurd (@h ((1) : Nat) ((2) : Nat) ?_ ?_ ?_) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Solve in positive integers the following equation:
\[{1\over n^2}-{3\over 2n^3}={1\over m^2}\]
 Prove that the answer is: (m, n) = (4, 2)

## fm_omni_theorem_325 — FALSE
- certificate: `¬ (type_of% @omni_theorem_325)`
- proof: `(intro h; refine absurd (@h ((0) : Nat) ((1) : Nat) ?_) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: Unknown identifier `X`

Note: It is not possible to treat `X` as an implicitly bound variable here because the `autoImplicit` option is set to `false`.
- informal: Let $N$ be the smallest positive integer for which $$x^{2}+x+1 \quad \text { divides } \quad 166-\sum_{d \mid N, d>0} x^{d}$$ Find the remainder when $N$ is divided by 1000.
 Prove that the answer is: \[ N \equiv 672 \pmod{1000} \]

## fm_olymid-ref-base_957 — FALSE
- certificate: `¬ (type_of% @olymid_ref_base_957)`
- proof: `(intro h; refine absurd (@h ((1) : Nat) ?_) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Prove that for any odd positive integer $n, n^{12}-n^{8}-n^{4}+1$ is divisible by $2^{9}$.

## fm_olymid-ref-base_2420 — FALSE
- certificate: `¬ (type_of% @olymid_ref_base_2420)`
- proof: `(intro h; refine absurd (@h ((0) : Nat) ((0) : Nat)) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Trouver tous les nombres premiers $p$ et $q$ tels que $p$ divise $5^{q}+1$ et $q$ divise $5^{p}+1$.
 Prove that the answer is: (2,2),(3,3),(13,2),(2,13),(3,7),(7,3)

## fm_olymid-ref-base_2472 — FALSE
- certificate: `¬ (type_of% @olymid_ref_base_2472)`
- proof: `(intro h; refine absurd (@h ((3) : Nat) ?_) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Trouver tous les entiers strictement positifs a tels que l'entier

$$
1-8 \cdot 3^{a}+2^{a+2}\left(2^{a}-1\right)
$$

soit un carré parfait.
 Prove that the answer is: 3 \text{ and } 5

## fm_olymid-ref-base_11810 — FALSE
- certificate: `¬ (type_of% @olymid_ref_base_11810)`
- proof: `(intro h; refine absurd (@h ((0) : Nat)) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Determine all positive integers $N$ for which there exists a strictly increasing sequence of positive integers $s_{0}<s_{1}<s_{2}<\cdots$ satisfying the following properties:  - the sequence $s_{1}-s_{0}, s_{2}-s_{1}, s_{3}-s_{2}, \ldots$ is periodic; and - $s_{s_{n}}-s_{s_{n-1}} \leq N<s_{1+s_{n}}-s_{s_{n-1}}$ for all positive integers $n$.
 Prove that the answer is: t^{2} \leq N<t^{2}+t

## fm_olymid-ref-base_4187 — FALSE
- certificate: `¬ (type_of% @olymid_ref_base_4187)`
- proof: `(intro h; refine absurd (@h ((0) : Real) ((1) : Real) ((2) : Real) ?_ ?_ ?_) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: real/rational witness — outside the prior audit's decide-over-integers counterexample search
- autobound: Unknown identifier `x`

Note: It is not possible to treat `x` as an implicitly bound variable here because the `autoImplicit` option is set to `false`.
- informal: Determine the positive real value of $x$ for which

$$
\sqrt{2+A C+2 C x}+\sqrt{A C-2+2 A x}=\sqrt{2(A+C) x+2 A C} .
$$
 Prove that the answer is: 4

## fm_omni_theorem_1467 — FALSE
- certificate: `¬ (type_of% @omni_theorem_1467)`
- proof: `(intro h; refine absurd (@h ((1) : Nat) ?_) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Find all positive integers $k<202$ for which there exists a positive integer $n$ such that $$\left\{\frac{n}{202}\right\}+\left\{\frac{2 n}{202}\right\}+\cdots+\left\{\frac{k n}{202}\right\}=\frac{k}{2}$$ where $\{x\}$ denote the fractional part of $x$.
 Prove that the answer is: k \in\{1,100,101,201\}

## fm_olymid-ref-base_5988 — FALSE
- certificate: `¬ (type_of% @olymid_ref_base_5988)`
- proof: `(intro h; refine absurd (@h ((0) : Nat)) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Let $f(x)=x^{2}+x+1$. Determine, with proof, all positive integers $n$ such that $f(k)$ divides $f(n)$ whenever $k$ is a positive divisor of $n$.
 Prove that the answer is: n = 1, \text{ a prime that is } 1 \bmod 3, \text{ or the square of any prime except 3}

## fm_olymid-ref-base_1859 — FALSE
- certificate: `¬ (type_of% @olymid_ref_base_1859)`
- proof: `(intro h; refine absurd (@h ((0) : Real) ((1) : Real) ((1) : Real) ?_ ?_ ?_) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: real/rational witness — outside the prior audit's decide-over-integers counterexample search
- autobound: None
- informal: (Netherlands). Find all triples $(a, b, c)$ of real numbers such that $a b+b c+$ $c a=1$ and

$$
a^{2} b+c=b^{2} c+a=c^{2} a+b
$$
 Prove that the answer is: None

## fm_u-math_404 — FALSE
- certificate: `¬ (type_of% @u_math_404)`
- proof: `(intro h; norm_num at h; done)`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Which equations have a common zero?

1. $x^2-11 \cdot x+28=0$
2. $x^2-5 \cdot x-84=0$
3. $x^2-11 \cdot x+30=0$
4. $x^2-14 \cdot x+49=0$
 Prove that the answer is: The final answer: $x^2-11\cdot x+28=0 \land x^2-14\cdot x+49=0$

## fm_omni_theorem_3815 — FALSE
- certificate: `¬ (type_of% @omni_theorem_3815)`
- proof: `(intro h; refine absurd (@h ((2) : Nat) ((0) : Nat) ((1) : Nat) ?_ ?_ ?_) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Find all prime numbers $p$ and nonnegative integers $x\neq y$ such that $x^4- y^4=p(x^3-y^3)$.
 Prove that the answer is: (p, x, y) = (p, p, 0) \text{ or } (p, 0, p)

## fm_olymid-ref-base_1073 — FALSE
- certificate: `¬ (type_of% @olymid)`
- proof: `(intro h; refine absurd (@h ((0) : Nat)) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Determine all positive integers $n$ for which there exists a set $S$ with the following properties:

(i) $S$ consists of $n$ positive integers, all smaller than $2^{n-1}$;

(ii) for any two distinct subsets $A$ and $B$ of $S$, the sum of the elements of $A$ is different from the sum of the elements of $B$.
 Prove that the answer is: n \geqslant 4

## fm_olymid-ref-base_10792 — FALSE
- certificate: `¬ (type_of% @olymid_ref_base_10792)`
- proof: `(intro h; refine absurd (@h ((0) : Nat) ((0) : Nat)) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Find all pairs of positive integers $(x, y)$ such that $2^{x}+3^{y}$ is a perfect square.
 Prove that the answer is: (4,2)

## fm_aime_all_2013_II_1 — FALSE
- certificate: `¬ (type_of% @aime_all_2013_II_1)`
- proof: `(intro h; refine absurd (@h ((0) : Nat) ((0) : Nat) ((4) : Nat) ?_ ?_ ?_ ?_) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Suppose that the measurement of time during the day is converted to the metric system so that each day has $10$ metric hours, and each metric hour has $100$ metric minutes. Digital clocks would then be produced that would read $\text{9:99}$ just before midnight, $\text{0:00}$ at midnight, $\text{1:25}$ at the former $\text{3:00}$ AM, and $\text{7:50}$ at the former $\text{6:00}$ PM. After the conversion, a person who wanted to wake up at the equivalent of the former $\text{6:36}$ AM would set hi

## fm_omni_theorem_3647 — FALSE
- certificate: `¬ (type_of% @omni_theorem_3647)`
- proof: `(intro h; refine absurd (@h ((0) : Nat)) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Find all positive integers $k<202$ for which there exist a positive integers $n$ such that
$$\bigg {\{}\frac{n}{202}\bigg {\}}+\bigg {\{}\frac{2n}{202}\bigg {\}}+\cdots +\bigg {\{}\frac{kn}{202}\bigg {\}}=\frac{k}{2}$$
 Prove that the answer is: 1, 100, 101, 201

## fm_aime_all_1995_2 — FALSE
- certificate: `¬ (type_of% @aime_all_1995_2)`
- proof: `(intro h; norm_num at h; done)`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Find the last three digits of the product of the positive roots of $\sqrt{1995}x^{\log_{1995}x}=x^2.$
 Prove that the answer is: 25

## fm_omni_theorem_515 — FALSE
- certificate: `¬ (type_of% @omni_theorem_515)`
- proof: `(intro h; refine absurd (@h ((0) : Real) ((0) : Real) ?_ ?_) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: real/rational witness — outside the prior audit's decide-over-integers counterexample search
- autobound: None
- informal: Let $(x, y)$ be a pair of real numbers satisfying $$56x+33y=\frac{-y}{x^{2}+y^{2}}, \quad \text { and } \quad 33x-56y=\frac{x}{x^{2}+y^{2}}$$ Determine the value of $|x|+|y|$.
 Prove that the answer is: \frac{11}{65}

## fm_aime_all_2014_II_4 — FALSE
- certificate: `¬ (type_of% @aime_all_2014_II_4)`
- proof: `(intro h; refine absurd (@h ((0) : Nat) ((0) : Nat) ((0) : Nat) ?_ ?_ ?_ ?_) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: The repeating decimals $0.abab\overline{ab}$ and $0.abcabc\overline{abc}$ satisfy $0.abab\overline{ab}+0.abcabc\overline{abc}=\frac{33}{37},$ where $a$ , $b$ , and $c$ are (not necessarily distinct) digits. Find the three digit number $abc$ .
 Prove that the answer is: 447

## fm_quantitative_reasoning_zh_blue_368 — FALSE
- certificate: `¬ (type_of% @quantitative_reasoning_zh_blue_368)`
- proof: `(intro h; refine absurd (@h ((3) : Nat) ?_) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: In a permutation \((a_1, a_2, \cdots, a_n)\) of \((1, 2, \cdots, n)\), if \(a_i\neq i\) (\(i = 1, 2, \cdots, n\)), then such a permutation is called a derangement (also known as a re - arrangement). Find the number \(D_n\) of derangements.

Proof: It is known that \(D_1 = 0\) and \(D_2 = 1\).

For \(n\geqslant3\) and any derangement \((a_1, a_2, \cdots, a_n)\) of \((1, 2, \cdots, n)\), \(a_1\) can take any of the \(n - 1\) numbers other than \(1\). Let \(a_1=k\) (\(k\neq1\)). Then:

(1) If \(a_k

## fm_omni_theorem_1748 — FALSE
- certificate: `¬ (type_of% @omni_theorem_1748)`
- proof: `decide`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Find the smallest positive integer $b$ such that $1111_{b}$ ( 1111 in base $b$) is a perfect square. If no such $b$ exists, write "No solution".
 Prove that the answer is: 7

## fm_olymid-ref-base_3054 — FALSE
- certificate: `¬ (type_of% @olymid_ref_base_3054)`
- proof: `(intro h; refine absurd (@h ((2) : Nat) ((4) : Nat)) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Man bestimme alle positiven ganzen Zahlen $k$ und $n$ mit folgender Eigenschaft:
Die Zahl $k^{4}+n^{2}$ ist ohne Rest durch die Zahl $7^{k}-3^{n}$ teilbar.
 Prove that the answer is: (k ; n)=(2 ; 4)

## fm_olymid-ref-base_2124 — FALSE
- certificate: `¬ (type_of% @olymid_ref_base_2124)`
- proof: `(intro h; refine absurd (@h ((0) : Real) ?_) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: real/rational witness — outside the prior audit's decide-over-integers counterexample search
- autobound: None
- informal: Soit $x \geqslant 0$ un réel. Montrer que :

$$
1+x^{2}+x^{6}+x^{8} \geqslant 4 x^{4}
$$

et trouver les cas d'égalité.

## fm_olymid-ref-base_3497 — FALSE
- certificate: `¬ (type_of% @olymid_ref_base_3497)`
- proof: `(intro h; norm_num at h; done)`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: (a) Decompose 1 into unit fractions.
 Prove that the answer is: \frac{1}{5}+\frac{1}{10}+\frac{1}{15}+\frac{1}{30}

## fm_u-math_292 — FALSE
- certificate: `¬ (type_of% @u_math_292)`
- proof: `(intro h; refine absurd (@h ((-2) : Rat)) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: real/rational witness — outside the prior audit's decide-over-integers counterexample search
- autobound: None
- informal: Multiply the rational expressions and express the product in simplest form:

$$
\frac{ 2 \cdot d^2 + d - 45 }{ d^2 + 7 \cdot d + 10 } \cdot \frac{ 4 \cdot d^2 + 7 \cdot d - 2 }{ 4 \cdot d^2 + 31 \cdot d - 8 }
$$
 Prove that the answer is: The final answer: $\frac{(2\cdot d-9)}{(d+8)}$

## fm_omni_theorem_4254 — FALSE
- certificate: `¬ (type_of% @omni_theorem_4254)`
- proof: `(intro h; refine absurd (@h ((0) : Nat) ((0) : Real)) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: real/rational witness — outside the prior audit's decide-over-integers counterexample search
- autobound: Unknown identifier `n`

Note: It is not possible to treat `n` as an implicitly bound variable here because the `autoImplicit` option is set to `false`.
- informal: Find, with proof, the smallest real number $C$ with the following property:
For every infinite sequence $\{x_i\}$ of positive real numbers such that $x_1 + x_2 +\cdots + x_n \leq x_{n+1}$ for $n = 1, 2, 3, \cdots$, we have
\[\sqrt{x_1}+\sqrt{x_2}+\cdots+\sqrt{x_n}  \leq C \sqrt{x_1+x_2+\cdots+x_n} \qquad \forall n \in \mathbb N.\]
 Prove that the answer is: $C=1+\sqrt{2}$

## fm_olymid-ref-base_4635 — FALSE
- certificate: `¬ (type_of% @olymid_ref_base_4635)`
- proof: `(intro h; refine absurd (@h ((0) : Int) ((0) : Int) ((0) : Int) ?_ ?_ ?_) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: The fraction $\frac{1}{2015}$ has a unique "(restricted) partial fraction decomposition" of the form

$$
\frac{1}{2015}=\frac{a}{5}+\frac{b}{13}+\frac{c}{31}
$$

where $a, b, c$ are integers with $0 \leq a<5$ and $0 \leq b<13$. Find $a+b$.
 Prove that the answer is: 14

## fm_omni_theorem_3461 — FALSE
- certificate: `¬ (type_of% @omni_theorem_3461)`
- proof: `(intro h; refine absurd (@h ((0) : Real)) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: real/rational witness — outside the prior audit's decide-over-integers counterexample search
- autobound: None
- informal: Which of the following expressions is not equivalent to $3x + 6$?
 Prove that the answer is: \frac{1}{3}(3x) + \frac{2}{3}(9)

## fm_olymid-ref-base_995 — FALSE
- certificate: `¬ (type_of% @olymid_ref_base_995)`
- proof: `(intro h; refine absurd (@h ((1) : Nat) ((10) : Nat) ?_ ?_ ?_ ?_) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: John is older than Mary. He notices that if he switches the two digits of his age (an integer), he gets Mary's age. Moreover, the difference between the squares of their ages is the square of an integer. How old are Mary and John?
 Prove that the answer is: 65, 56

## fm_olymid-ref-base_3256 — FALSE
- certificate: `¬ (type_of% @olymid_ref_base_3256)`
- proof: `(intro h; refine absurd (@h ((2) : Nat) ?_) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Find all positive integers $n$ such that

$$
\sum_{k=1}^{n} \phi(k)=\frac{3 n^{2}+5}{8}
$$
 Prove that the answer is: 1, 3, 5

## fm_omni_theorem_919 — FALSE
- certificate: `¬ (type_of% @omni_theorem_919)`
- proof: `(intro h; refine absurd (@h ((1) : Real) ((1) : Real) ((1) : Real) ?_ ?_ ?_ ?_) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: real/rational witness — outside the prior audit's decide-over-integers counterexample search
- autobound: None
- informal: Given that $a, b, c$ are positive real numbers and $\log _{a} b+\log _{b} c+\log _{c} a=0$, find the value of $\left(\log _{a} b\right)^{3}+\left(\log _{b} c\right)^{3}+\left(\log _{c} a\right)^{3}$.
 Prove that the answer is: 3

## fm_omni_theorem_4047 — FALSE
- certificate: `¬ (type_of% @omni_theorem_4047)`
- proof: `(intro h; refine absurd (@h ((0) : Nat)) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Find all positive integers $n\geq1$ such that there exists a pair $(a,b)$ of positive integers, such that $a^2+b+3$ is not divisible by the cube of any prime, and $$n=\frac{ab+3b+8}{a^2+b+3}.$$
 Prove that the answer is: 2

## fm_olymid-ref-base_9492 — FALSE
- certificate: `¬ (type_of% @olymid_ref_base_9492)`
- proof: `(intro h; refine absurd (@h ((0) : Nat) ((0) : Nat) ?_ ?_) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: 10. (FRG 1) (SL77-3).
 Prove that the answer is: (a, b) \in\{(7,50),(37,50),(50,7),(50,37)\}

## fm_olymid-ref-base_11002 — FALSE
- certificate: `¬ (type_of% @olymid_ref_base_11002)`
- proof: `(intro h; refine absurd (@h ((10) : Nat) ?_) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Find all positive integers $k$ such that the product of the digits of $k$, in the decimal system, equals

$$
\frac{25}{8} k-211
$$
 Prove that the answer is: 72, 88

## fm_olymid-ref-base_10553 — FALSE
- certificate: `¬ (type_of% @olymid_ref_base_10553)`
- proof: `(intro h; refine absurd (@h ((1) : Real) ((-1) : Real) ((1) : Real) ?_ ?_ ?_ ?_ ?_) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: real/rational witness — outside the prior audit's decide-over-integers counterexample search
- autobound: None
- informal: Find all triples $(a, b, c)$ of real numbers such that the following system holds:

$$
\left\{\begin{array}{l}
a+b+c=\frac{1}{a}+\frac{1}{b}+\frac{1}{c} \\
a^{2}+b^{2}+c^{2}=\frac{1}{a^{2}}+\frac{1}{b^{2}}+\frac{1}{c^{2}}
\end{array}\right.
$$
 Prove that the answer is: (a, b, c)=\left(t, \frac{1}{t}, 1\right),\left(t, \frac{1}{t},-1\right)

## fm_quantitative_reasoning_zh_blue_208 — FALSE
- certificate: `¬ (type_of% @quantitative_reasoning_zh_blue_208)`
- proof: `(intro h; refine absurd (@h ((1) : Nat) ?_) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Divide each side of an equilateral triangle into \(n\) equal parts. Through the division points, draw lines parallel to the sides inside the equilateral triangle to divide the equilateral triangle into small equilateral triangles. The questions are: (1) How many equilateral triangles are there (including the original equilateral triangle)? (2) How many rhombuses are there?

Proof:
(1) The number of equilateral triangles with side length \(k\) and “pointing upwards” is \(x_k = 1 + 2+\cdots+[n-(k 

## fm_u-math_820 — FALSE
- certificate: `¬ (type_of% @u_math_820)`
- proof: `(intro h; refine absurd (@h ((0) : Real)) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: real/rational witness — outside the prior audit's decide-over-integers counterexample search
- autobound: None
- informal: Simplify the expression $\sin(x) \cdot \left(\csc(x)-\sin(x)\right)$ by writing it in terms of sines and cosines, then simplify. The final answer does not have to be in terms of sine and cosine only.
 Prove that the answer is: $\sin(x) \cdot \left(\csc(x)-\sin(x)\right)$ = $\cos(x)^2$

## fm_olymid-ref-base_8490 — FALSE
- certificate: `¬ (type_of% @olymid_ref_base_8490)`
- proof: `(intro h; refine absurd (@h ((2) : Nat)) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Determine all positive integers $M$ for which the sequence $a_{0}, a_{1}, a_{2}, \ldots$, defined by $a_{0}=\frac{2 M+1}{2}$ and $a_{k+1}=a_{k}\left\lfloor a_{k}\right\rfloor$ for $k=0,1,2, \ldots$, contains at least one integer term. (Luxembourg)
 Prove that the answer is: M=1

## fm_u-math_552 — FALSE
- certificate: `¬ (type_of% @u_math_552)`
- proof: `(intro h; refine absurd (@h ((0) : Real) ((0) : Real) ?_) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: real/rational witness — outside the prior audit's decide-over-integers counterexample search
- autobound: Unknown identifier `x`

Note: It is not possible to treat `x` as an implicitly bound variable here because the `autoImplicit` option is set to `false`.
- informal: If $\tan(\theta) = \sqrt{x^2 - 1}$, find $\sec(\theta) + \tan(\theta)$.
 Prove that the answer is: $\sec(\theta) + \tan(\theta)$ = $x+\sqrt{x^2-1}$ (Enter your solution as an expression using only the variable $x$.)

## fm_olymid-ref-base_435 — FALSE
- certificate: `¬ (type_of% @olymid_ref_base_435)`
- proof: `(intro h; refine absurd (@h ((0) : Nat)) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Find all positive integers $n$ such that $n$ is equal to 100 times the number of positive divisors of $n$.
 Prove that the answer is: 2000

## fm_omni_theorem_372 — FALSE
- certificate: `¬ (type_of% @omni_theorem_372)`
- proof: `(norm_num; done)`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: For the following planar graphs, determine the number of vertices $v$, edges $e$, and faces $f$: i. $v=9, e=16, f=9$; ii. $v=7, e=14, f=9$. Verify Euler's formula $v-e+f=2$.
 Prove that the answer is: i. Euler's formula holds; ii. Euler's formula holds

## fm_omni_theorem_298 — FALSE
- certificate: `¬ (type_of% @omni_theorem_298)`
- proof: `(intro h; refine absurd (@h ((1) : Nat) ((1) : Nat) ?_ ?_) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Find all pairs of positive integers $(x,y)$ such that \[x^y = y^{x - y}.\]
 Prove that the answer is: The pairs of positive integers \((x, y)\) that satisfy the equation \(x^y = y^{x - y}\) are:

\[
(x, y) = (9, 3) \quad \text{and} \quad (x, y) = (8, 2)
\]

## fm_olymid-ref-base_2929 — FALSE
- certificate: `¬ (type_of% @olymid_ref_base_2929)`
- proof: `(intro h; refine absurd (@h ((0) : Nat)) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Trouver les entiers $n$ pour lesquels l'égalité

$$
\sum_{i=1}^{n} \sum_{j=1}^{n}\left\lfloor\frac{i \times j}{n+1}\right\rfloor=\frac{n^{2}(n-1)}{4}
$$

est vérifiée.
On rappelle que, pour tout nombre réel $x$, la notation $\lfloor x\rfloor$ désigne la partie entière de $x$, c'est-à-dire le plus grand entier inférieur ou égal à $x$.
 Prove that the answer is: n+1 \text{ est premier}

## fm_quantitative_reasoning_zh_blue_52 — FALSE
- certificate: `¬ (type_of% @quantitative_reasoning_zh_blue_52)`
- proof: `(intro h; refine absurd (@h ((0) : Real) ((0) : Real)) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: real/rational witness — outside the prior audit's decide-over-integers counterexample search
- autobound: Unknown identifier `I`

Note: It is not possible to treat `I` as an implicitly bound variable here because the `autoImplicit` option is set to `false`.
- informal: It is known that there are two sets of complex numbers \(M = \{z\mid z = \cos\alpha+(4 - \cos^{2}\alpha)i,\alpha\in R\}\), \(N=\{z\mid z=\cos\beta+(\lambda+\sin\beta)i,\beta\in R\}\). When \(M\cap N\neq\varnothing\), the range of the real number \(\lambda\) is to be found.

Prove that the answer is \(\left[\frac{11}{4},5\right]\). Let \(\cos\alpha+(4 - \cos^{2}\alpha)i=\cos\beta+(\lambda+\sin\beta)i\). Then we have \(\cos\alpha=\cos\beta\) and \(4 - \cos^{2}\alpha=\lambda+\sin\beta\). Eliminatin

## fm_quantitative_reasoning_zh_blue_230 — FALSE
- certificate: `¬ (type_of% @quantitative_reasoning_zh_blue_230)`
- proof: `(intro h; refine absurd (@h ((1) : Nat) ?_) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: First, take a subset \(X\) from the set \(S = \{1, 2,\cdots, n\}(n\in\mathbf{N}_{+})\), and then take a subset \(Y\) such that \(X\) is not a subset of \(Y\) and \(Y\) is not a subset of \(X\). How many different ways of such an ordered selection are there?

Prove that the answer is: Since there are \(2^{n}\) subsets in \(S\), when \(X\neq Y\), the number of ways to select two different subsets \(X\) and \(Y\) from \(S\) in an ordered manner is \(A_{2^{n}}^{2}=2^{n}(2^{n} - 1)\) ways.

Subtract 

## fm_olymid-ref-base_9254 — FALSE
- certificate: `¬ (type_of% @olymid_ref_base_9254)`
- proof: `(intro h; refine absurd (@h ((1) : Real)) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: real/rational witness — outside the prior audit's decide-over-integers counterexample search
- autobound: None
- informal: 2. (ROM) For which real numbers $x$ do the following equations hold: (a) $\sqrt{x+\sqrt{2 x-1}}+\sqrt{x+\sqrt{2 x-1}}=\sqrt{2}$, (b) $\sqrt{x+\sqrt{2 x-1}}+\sqrt{x+\sqrt{2 x-1}}=1$, (c) $\sqrt{x+\sqrt{2 x-1}}+\sqrt{x+\sqrt{2 x-1}}=2$ ?
 Prove that the answer is: a) 1 / 2 \leq x \leq 1, \quad b) \text{no solution}, \quad c) x = 3 / 2

## fm_olymid-ref-base_2012 — VACUOUS
- certificate: `vacuous_of% @olymid_ref_base_2012`
- proof: `(intros; simp_all; done)`
- novelty: contradiction found by omega/simp — may overlap the prior audit
- autobound: None
- informal: La suite ( $a_{n}$ ) est définie par $a_{1}=1$ et

$$
a_{n}=\frac{1}{n}+\frac{1}{a_{1} \cdot \ldots \cdot a_{n-1}}
$$

Montrer que pour tout entier $m \geqslant 3$, on a $a_{m} \leqslant 1$.

## fm_omni_theorem_745 — FALSE
- certificate: `¬ (type_of% @omni_theorem_745)`
- proof: `(intro h; norm_num at h; done)`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Let $a, b$ be integers chosen independently and uniformly at random from the set $\{0,1,2, \ldots, 80\}$. Compute the expected value of the remainder when the binomial coefficient $\binom{a}{b}=\frac{a!}{b!(a-b)!}$ is divided by 3.
 Prove that the answer is: \frac{1816}{6561}

## fm_omni_theorem_4220 — FALSE
- certificate: `¬ (type_of% @omni_theorem_4220)`
- proof: `(intro h; refine absurd (@h ((0) : Nat)) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Find all positive integers $ n$ for which the numbers in the set $ S \equal{} \{1,2, \ldots,n \}$ can be colored red and blue, with the following condition being satisfied: The set $ S \times S \times S$ contains exactly $ 2007$ ordered triples $ \left(x, y, z\right)$ such that:

[b](i)[/b] the numbers $ x$, $ y$, $ z$ are of the same color,
and
[b](ii)[/b] the number $ x \plus{} y \plus{} z$ is divisible by $ n$.

[i]Author: Gerhard W?ginger, Netherlands[/i]
 Prove that the answer is: n \in \{6

## fm_u-math_291 — FALSE
- certificate: `¬ (type_of% @u_math_291)`
- proof: `(intro h; refine absurd (@h ((2) : Real) ?_) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: real/rational witness — outside the prior audit's decide-over-integers counterexample search
- autobound: None
- informal: Use the properties of logarithms to expand the logarithm $\ln\left(y \cdot \sqrt{\frac{ y }{ 1-y }}\right)$ as much as possible. Rewrite the expression as a sum, difference, or product of logs.
 Prove that the answer is: The final answer: $\frac{3}{2}\cdot\ln(y)-\frac{1}{2}\cdot\ln(1-y)$

## fm_u-math_1091 — FALSE
- certificate: `¬ (type_of% @u_math_1091)`
- proof: `(intro h; refine absurd (@h ((-2) : Real) ?_) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: real/rational witness — outside the prior audit's decide-over-integers counterexample search
- autobound: None
- informal: Multiply the rational expressions and express the product in simplest form:

$$
\frac{ x^2-x-6 }{ 2 \cdot x^2+x-6 } \cdot \frac{ 2 \cdot x^2+7 \cdot x-15 }{ x^2-9 }
$$
 Prove that the answer is: The final answer: $\frac{x+5}{x+3}$

## fm_omni_theorem_578 — FALSE
- certificate: `¬ (type_of% @omni_theorem_578)`
- proof: `(intro h; refine absurd (@h ((0) : Nat)) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Find, as a function of $\, n, \,$ the sum of the digits of \[9 \times 99 \times 9999 \times \cdots \times \left( 10^{2^n} - 1 \right),\] where each factor has twice as many digits as the previous one.
 Prove that the answer is: \[ 9 \cdot 2^n \]

## fm_olymid-ref-base_10823 — FALSE
- certificate: `¬ (type_of% @olymid_ref_base_10823)`
- proof: `(intro h; refine absurd (@h ((1) : Nat) ((2) : Nat) ((1) : Nat)) ?_ <;> first | decide | (norm_num; done) | omega | positivity | linarith | (simp; done) | (norm_num at *; done) | (simp at *; done))`
- novelty: integer/natural witness — may overlap the prior audit's small-domain search
- autobound: None
- informal: Find all triples $(a, b, c)$ of nonnegative integers that satisfy

$$
a!+5^{b}=7^{c}
$$
 Prove that the answer is: (3,0,1),(1,2,1),(4,2,2)


Finding nothing is not evidence that a statement is correct; COMPILE_FAIL rows are version drift, not defects.
