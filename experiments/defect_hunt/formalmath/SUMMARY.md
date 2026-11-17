# FormalMATH defect hunt — 2224 statements checked

**Controls: PASS** — ctrl_false_real: expected FALSE, certified ['FALSE']; ctrl_false_int: expected FALSE, certified ['FALSE']; ctrl_vacuous: expected VACUOUS, certified ['VACUOUS']; ctrl_true: expected None, certified []

Data `SphereLab/FormalMATH-All` · Lean 4.34.1 · Mathlib `d13f23b` · engine `proofscope/defect_hunt.py`

| Outcome | Count |
|---|---:|
| CANDIDATE | 50 |
| COMPILE_FAIL | 31 |
| NO_DEFECT_FOUND | 2128 |
| SKIP_NO_THEOREM | 13 |
| SKIP_PLACEHOLDER | 1 |
| SKIP_UNIVERSE_POLY | 1 |

**Certified findings: 50** (each re-proved in a clean module, standard axioms only, leanchecker replay).

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

Shards without a summary (job failed): [1, 3, 6, 7, 9, 11, 12, 13, 14, 17, 18, 19]

Finding nothing is not evidence that a statement is correct; COMPILE_FAIL rows are version drift, not defects.
