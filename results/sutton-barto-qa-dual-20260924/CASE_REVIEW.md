# QA逐题核查

## AutoSchemaKG / rl-qa-ch01-1

任务：t_1babd2ea78d30e447982adfb

Do all of the reinforcement learning methods considered in the book estimate value functions, and what counter-examples does the book give?

旧：pass；核心：pass；完整：pass

- R1 核心：The answer is no — not all of the reinforcement learning methods considered in the book estimate value functions.
  判定：pass；C1 and C2 both indicate that only 'most' (not all) reinforcement learning methods considered in the book estimate value functions, and C2 explicitly notes that some methods (genetic algorithms, genetic programming, simulated annealing, other optimization methods) 'never estimate value functions,' supporting the answer 'no.'
  C2.object：Solution methods such as genetic algorithms, genetic programming, simulated annealing, and other optimization methods never estimate value functions
  C1.subject：The concepts of value and value function are key to most of the reinforcement learning methods considered in the book.
- R2 核心：Most of the methods considered in the book are structured around estimating value functions, but this is not strictly necessary to solve reinforcement learning problems.
  判定：pass；C2 explicitly states 'Most of the reinforcement learning methods we consider in this book are structured around estimating value functions,' and the same candidate notes that other methods (genetic algorithms, etc.) 'never estimate value functions,' implying that value function estimation is not strictly necessary. C1 corroborates the 'most' framing.
  C2.subject：Most of the reinforcement learning methods we consider in this book are structured around estimating value functions
  C2.object：Solution methods such as genetic algorithms, genetic programming, simulated annealing, and other optimization methods never estimate value functions
- R3 核心：The book gives genetic algorithms, genetic programming, simulated annealing, and other optimization methods as counter-examples of solution methods that never estimate value functions.
  判定：pass；C2 explicitly names genetic algorithms, genetic programming, simulated annealing, and other optimization methods as solution methods that 'never estimate value functions.' C4 reinforces this by listing these same three as examples of solution methods that never estimate value functions.
  C2.object：Solution methods such as genetic algorithms, genetic programming, simulated annealing, and other optimization methods never estimate value functions
  C4.object：solution methods that never estimate value functions

## GraphRAG / rl-qa-ch01-1

任务：t_e16dda3d62376865548a6180

Do all of the reinforcement learning methods considered in the book estimate value functions, and what counter-examples does the book give?

旧：fail；核心：uncertain；完整：uncertain

- R1 核心：The answer is no — not all of the reinforcement learning methods considered in the book estimate value functions.
  判定：pass；Multiple candidates support that not all RL methods estimate value functions. C2 directly states evolutionary methods never estimate value functions, contrasting with most RL methods. C4 says 'almost all' and C7 says 'nearly all,' both implying exceptions exist.
  C2.text：Evolutionary methods never estimate value functions, in contrast to most reinforcement learning methods
  C4.text：Almost all reinforcement learning algorithms involve estimating value functions
  C7.text：Sutton and Barto present value functions as a core concept in nearly all reinforcement learning algorithms
- R2 核心：Most of the methods considered in the book are structured around estimating value functions, but this is not strictly necessary to solve reinforcement learning problems.
  判定：pass；Candidates support both parts: C6 states 'most reinforcement learning methods being structured around the estimation of value functions,' supporting the 'most' claim. C2's statement that evolutionary methods solve RL without estimating value functions supports the 'not strictly necessary' claim.
  C6.text：most reinforcement learning methods being structured around the estimation of value functions
  C2.text：Evolutionary methods never estimate value functions, in contrast to most reinforcement learning methods
- R3 核心：The book gives genetic algorithms, genetic programming, simulated annealing, and other optimization methods as counter-examples of solution methods that never estimate value functions.
  判定：uncertain；C2 only generically references 'Evolutionary methods' as never estimating value functions. While genetic algorithms and genetic programming are a subset of evolutionary methods, simulated annealing is not typically classified as an evolutionary method. No candidate explicitly enumerates genetic algorithms, genetic programming, and simulated annealing as the specific counter-examples.
  C2.text：Evolutionary methods never estimate value functions, in contrast to most reinforcement learning methods

## KGGen / rl-qa-ch01-1

任务：t_93a640398b6e8a80831d4456

Do all of the reinforcement learning methods considered in the book estimate value functions, and what counter-examples does the book give?

旧：pass；核心：fail；完整：fail

- R1 核心：The answer is no — not all of the reinforcement learning methods considered in the book estimate value functions.
  判定：pass；C1 states that learning methods estimate value functions, while C2 states that optimization methods do not estimate value functions. Together these imply that not all methods considered estimate value functions, supporting the 'no' answer.
  C1.text：learning methods estimate value functions
  C2.text：optimization methods do not estimate Value function
- R2 核心：Most of the methods considered in the book are structured around estimating value functions, but this is not strictly necessary to solve reinforcement learning problems.
  判定：pass；C1 supports the 'most methods are structured around estimating value functions' part, and C2 supports the 'not strictly necessary' part by showing there exist methods (optimization methods) that do not estimate value functions.
  C1.text：learning methods estimate value functions
  C2.text：optimization methods do not estimate Value function
- R3 核心：The book gives genetic algorithms, genetic programming, simulated annealing, and other optimization methods as counter-examples of solution methods that never estimate value functions.
  判定：fail；C2 only mentions 'optimization methods' generically but does not name the specific counter-examples required: genetic algorithms, genetic programming, and simulated annealing. The specific examples are missing from the candidates.
  C2.text：optimization methods do not estimate Value function

## 我们的方法（强化学习） / rl-qa-ch01-1

任务：t_c375ac9a4a9b2b9c8d167dc7

Do all of the reinforcement learning methods considered in the book estimate value functions, and what counter-examples does the book give?

旧：fail；核心：fail；完整：fail

- R1 核心：The answer is no — not all of the reinforcement learning methods considered in the book estimate value functions.
  判定：pass；C9 states that 'Most' (not all) of the reinforcement learning methods considered in the book are structured around estimating value functions, which directly supports the claim that not all methods estimate value functions.
  C9.text：Most of the 强化学习 methods considered in this book are structured around estimating 值函数（强化学习）s.
- R2 核心：Most of the methods considered in the book are structured around estimating value functions, but this is not strictly necessary to solve reinforcement learning problems.
  判定：pass；C9 directly supports the first clause ('most of the methods are structured around estimating value functions'). The word 'Most' logically implies not all, which entails that estimating value functions is not strictly necessary to solve RL problems, supporting the second clause through direct semantic inference.
  C9.text：Most of the 强化学习 methods considered in this book are structured around estimating 值函数（强化学习）s.
- R3 核心：The book gives genetic algorithms, genetic programming, simulated annealing, and other optimization methods as counter-examples of solution methods that never estimate value functions.
  判定：fail；No candidate mentions genetic algorithms, genetic programming, simulated annealing, or other optimization methods as counter-examples of solution methods that never estimate value functions. None of the provided candidates contain this information.

## AutoSchemaKG / rl-qa-ch01-2

任务：t_b0868d7d4c5a6af0dc0d9113

How does the book distinguish rewards from value functions in a reinforcement learning system?

旧：fail；核心：fail；完整：fail

- R1 核心：The reward signal indicates what is good in an immediate sense and defines what are the good and bad events for the agent.
  判定：fail；No candidate discusses the reward signal indicating what is good in an immediate sense or defining good and bad events for the agent. None of the candidates address the immediate nature of the reward signal.
- R2 核心：A value function specifies what is good in the long run: the total amount of reward an agent can expect to accumulate over the future, taking into account the states that are likely to follow and the rewards available in those states.
  判定：pass；C9 directly states that 'A policy's value functions assign to each state the expected return from that state' and that 'The return is the function of future rewards that the agent seeks to maximize in expected value.' This captures the core idea that value functions specify the total amount of reward an agent can expect to accumulate over the future (the long run), which aligns with the requirement.
  C9.text：A policy's value functions assign to each state the expected return from that state given that the agent uses the policy.
  C9.text：The return is the function of future rewards that the agent seeks to maximize in expected value.
- R3 核心：Rewards are primary and are given directly by the environment, whereas values are secondary predictions of rewards that must be estimated and re-estimated from the sequences of observations an agent makes.
  判定：fail；No candidate explicitly contrasts rewards as primary signals given by the environment with values as secondary predictions that must be estimated. C5 and C8 mention estimating value functions, but none address the primary/secondary distinction or the environmental origin of rewards.
- R4 完整答案补充：Action choices are made based on value judgments (seeking states of highest value), not directly on reward, because values capture long-term reward accumulation.
  判定：fail；No candidate directly states that action choices are made based on value judgments rather than directly on reward. C1 mentions value functions are important for efficient search in the space of policies, which is tangentially related but does not establish the specific claim that actions seek states of highest value rather than reacting to immediate reward.
- R5 完整答案补充：A state may yield a low immediate reward but still have a high value (because it is regularly followed by high-reward states), or vice versa.
  判定：fail；No candidate discusses the possibility that a state may yield a low immediate reward but have a high value, or vice versa. None of the candidates address this disjunction between immediate reward and state value.

## GraphRAG / rl-qa-ch01-2

任务：t_adab56d219ae9e515c5db35c

How does the book distinguish rewards from value functions in a reinforcement learning system?

旧：fail；核心：fail；完整：fail

- R1 核心：The reward signal indicates what is good in an immediate sense and defines what are the good and bad events for the agent.
  判定：fail；No candidate addresses the immediacy of rewards or that the reward signal defines good and bad events for the agent. C10 only states values estimate expected return composed of rewards, which is about value functions, not the immediate nature of rewards.
- R2 核心：A value function specifies what is good in the long run: the total amount of reward an agent can expect to accumulate over the future, taking into account the states that are likely to follow and the rewards available in those states.
  判定：pass；C1 directly states that value functions estimate how good a state or action is in terms of expected future rewards, which captures the core idea of value functions specifying what is good in the long run in terms of total expected future reward.
  C1.text：Value functions estimate how good a state or action is in terms of expected future rewards
- R3 核心：Rewards are primary and are given directly by the environment, whereas values are secondary predictions of rewards that must be estimated and re-estimated from the sequences of observations an agent makes.
  判定：fail；No candidate explicitly distinguishes rewards as primary signals given directly by the environment versus values as secondary predictions estimated from sequences of observations. C10 only states values estimate expected return composed of rewards, but does not address the primary/secondary distinction or the observation-based estimation process.
  C10.text：Value functions estimate the expected return, which is composed of rewards
- R4 完整答案补充：Action choices are made based on value judgments (seeking states of highest value), not directly on reward, because values capture long-term reward accumulation.
  判定：uncertain；C6 supports that agents relying on value functions select actions by ascending the gradient of their value function, which covers action choices being based on value judgments. However, no candidate explicitly states that action choices are NOT made directly on reward, nor that this is because values capture long-term reward accumulation. The 'not directly on reward' distinction is missing from the candidates.
  C6.text：Reinforcement learning agents that rely on value functions select their actions by ascending the gradient of their value function, using this learned estimate to guide decision-making
- R5 完整答案补充：A state may yield a low immediate reward but still have a high value (because it is regularly followed by high-reward states), or vice versa.
  判定：fail；No candidate addresses the scenario where a state may have low immediate reward but high value, or vice versa. The candidates discuss value functions estimating expected future rewards but do not provide the specific illustration of discrepancy between immediate reward and long-term value.

## KGGen / rl-qa-ch01-2

任务：t_46def11ddefaab542c12ea29

How does the book distinguish rewards from value functions in a reinforcement learning system?

旧：fail；核心：fail；完整：fail

- R1 核心：The reward signal indicates what is good in an immediate sense and defines what are the good and bad events for the agent.
  判定：fail；No candidate states that the reward signal indicates what is good in an immediate sense or defines good and bad events for the agent. C1 only says 'Learning learns how environment generates rewards,' which does not convey the immediacy or the good/bad event definition.
- R2 核心：A value function specifies what is good in the long run: the total amount of reward an agent can expect to accumulate over the future, taking into account the states that are likely to follow and the rewards available in those states.
  判定：fail；C9 only says value functions 'estimate how good it is for agent to be in state–action pair.' It does not mention long-term accumulation, total expected reward over the future, or states likely to follow—key components of the requirement.
  C9.text：value functions estimate how good it is for agent to be in state–action pair
- R3 核心：Rewards are primary and are given directly by the environment, whereas values are secondary predictions of rewards that must be estimated and re-estimated from the sequences of observations an agent makes.
  判定：fail；No candidate addresses that rewards are primary and given directly by the environment, nor that values are secondary predictions estimated from observations. C1 only mentions the environment generating rewards without establishing the primary/secondary distinction.
- R4 完整答案补充：Action choices are made based on value judgments (seeking states of highest value), not directly on reward, because values capture long-term reward accumulation.
  判定：fail；No candidate discusses action choices being made based on value judgments or seeking states of highest value. The candidates only discuss value functions in general terms without relating them to action selection.
- R5 完整答案补充：A state may yield a low immediate reward but still have a high value (because it is regularly followed by high-reward states), or vice versa.
  判定：fail；No candidate mentions the relationship where a state can have low immediate reward but high value (or vice versa). C9 only generally states value functions estimate goodness of a state–action pair, without illustrating the contrast with immediate reward.

## 我们的方法（强化学习） / rl-qa-ch01-2

任务：t_b8b20ab52d20a63ccb38a870

How does the book distinguish rewards from value functions in a reinforcement learning system?

旧：fail；核心：fail；完整：fail

- R1 核心：The reward signal indicates what is good in an immediate sense and defines what are the good and bad events for the agent.
  判定：fail；No candidate discusses the reward signal indicating what is good in an immediate sense or defining good and bad events for the agent.
- R2 核心：A value function specifies what is good in the long run: the total amount of reward an agent can expect to accumulate over the future, taking into account the states that are likely to follow and the rewards available in those states.
  判定：fail；No candidate discusses value functions as specifying long-term total expected reward accounting for likely future states. C7 mentions GVFs predicting cumulants but does not explain the long-run definition of value functions.
- R3 核心：Rewards are primary and are given directly by the environment, whereas values are secondary predictions of rewards that must be estimated and re-estimated from the sequences of observations an agent makes.
  判定：fail；No candidate addresses the distinction that rewards are primary and given by the environment while values are secondary predictions that must be estimated from observation sequences.
- R4 完整答案补充：Action choices are made based on value judgments (seeking states of highest value), not directly on reward, because values capture long-term reward accumulation.
  判定：fail；No candidate discusses action choices being based on value judgments rather than direct reward.
- R5 完整答案补充：A state may yield a low immediate reward but still have a high value (because it is regularly followed by high-reward states), or vice versa.
  判定：fail；No candidate addresses the case where a state may have low immediate reward but high value (or vice versa).

## AutoSchemaKG / rl-qa-ch02-1

任务：t_89b8e2ebce6952767358d1b4

In the slot-machine example illustrating an associative search task, what kind of information is provided to the learner about each bandit task, and what example policy is given?

旧：fail；核心：fail；完整：fail

- R1 核心：The learner is given a distinctive clue about the identity of each bandit task, but not its action values.
  判定：pass；C4 explicitly states that 'when a bandit task is selected, you are given some distinctive clue about its identity,' which directly supports the requirement that the learner receives a distinctive clue about the task's identity (and by specifying 'identity' as the content, distinguishes it from action values).
  C4.text：Now suppose that when a bandit task is selected, you are given some distinctive clue about its identity.
- R2 完整答案补充：In the slot machine example, the machine changes the color of its display as it changes its action values, serving as the distinctive clue.
  判定：fail；No candidate mentions the slot machine changing the color of its display as it changes its action values, nor anything about a visual/color-based distinctive clue.
- R3 核心：The example policy given is: if red, select arm 1; if green, select arm 2.
  判定：fail；No candidate provides the specific example policy of 'if red, select arm 1; if green, select arm 2.' Candidates only reference the general concept of 'a policy associating each task with the best action to take' (C1, C4, C8) without specifying the red/green, arm 1/arm 2 example.

## GraphRAG / rl-qa-ch02-1

任务：t_55ff93e0bada3af27393e898

In the slot-machine example illustrating an associative search task, what kind of information is provided to the learner about each bandit task, and what example policy is given?

旧：fail；核心：fail；完整：fail

- R1 核心：The learner is given a distinctive clue about the identity of each bandit task, but not its action values.
  判定：pass；C9 states a distinctive clue (e.g., color) identifies the bandit task, and C3 states the agent is told which case it faces on each step. Together they support that the learner is given a distinctive clue about the identity but not the action values.
  C9.text：A distinctive clue such as a color identifies the bandit task in the associative search setting
  C3.text：The associative search task is a variant of the 2-armed bandit task in which the agent is told which case it faces on each step
- R2 完整答案补充：In the slot machine example, the machine changes the color of its display as it changes its action values, serving as the distinctive clue.
  判定：pass；C1 directly states the slot machine changes color as its action values change and is used as an associative search task example, matching the description of the color serving as the distinctive clue.
  C1.text：A slot machine that changes color as its action values change is used as an example of an associative search task
- R3 核心：The example policy given is: if red, select arm 1; if green, select arm 2.
  判定：fail；No candidate mentions a specific example policy such as 'if red, select arm 1; if green, select arm 2.' None of the provided assertions describe any policy or action selection rule.

## KGGen / rl-qa-ch02-1

任务：t_10c4f8b4de47d0b5c6dd100a

In the slot-machine example illustrating an associative search task, what kind of information is provided to the learner about each bandit task, and what example policy is given?

旧：fail；核心：fail；完整：fail

- R1 核心：The learner is given a distinctive clue about the identity of each bandit task, but not its action values.
  判定：fail；No candidate asserts that the learner is given a distinctive clue about each bandit task's identity, nor that action values are withheld. The closest candidates (C5: 'learner faces bandit task'; C6: 'learner associated_with bandit task') do not describe the nature of the information provided.
- R2 完整答案补充：In the slot machine example, the machine changes the color of its display as it changes its action values, serving as the distinctive clue.
  判定：fail；No candidate mentions the slot machine changing the color of its display or action values changing. Candidates only state general analogies (C2, C3) without describing display colors or value changes.
- R3 核心：The example policy given is: if red, select arm 1; if green, select arm 2.
  判定：fail；No candidate provides an example policy involving red/green colors and specific arm selections. The candidates discuss the general relationship between associative search and bandit problems but give no concrete policy.

## 我们的方法（强化学习） / rl-qa-ch02-1

任务：t_7af750756a5cbcf57a259d40

In the slot-machine example illustrating an associative search task, what kind of information is provided to the learner about each bandit task, and what example policy is given?

旧：fail；核心：fail；完整：fail

- R1 核心：The learner is given a distinctive clue about the identity of each bandit task, but not its action values.
  判定：fail；No candidate describes that the learner is given a distinctive clue about the identity of each bandit task but not its action values. C1 only describes the general nature of the associative setting; none address what information is provided to the learner.
- R2 完整答案补充：In the slot machine example, the machine changes the color of its display as it changes its action values, serving as the distinctive clue.
  判定：fail；No candidate mentions the slot machine changing the color of its display as it changes its action values. None of the candidates discuss color changes or the slot machine serving as a distinctive clue.
- R3 核心：The example policy given is: if red, select arm 1; if green, select arm 2.
  判定：fail；No candidate provides the example policy of 'if red, select arm 1; if green, select arm 2.' None of the candidates discuss color-based action selection policies.

## AutoSchemaKG / rl-qa-ch02-2

任务：t_c348f14d8c7fb33cd64458ca

How can optimistic initial action-value estimates encourage exploration even when actions are selected greedily?

旧：pass；核心：fail；完整：fail

- R1 核心：Optimistic initial action-value estimates are set higher than the true expected rewards, so the initial estimate for any action exceeds the rewards that action will actually yield.
  判定：pass；Candidates C8 and C10 directly state that initial action values are set to +5 while true values are drawn from a distribution with mean 0, and that +5 is wildly optimistic, supporting that initial estimates exceed true expected rewards.
  C10.text：The initial action values are set to +5 while the true values are drawn from a distribution with mean 0. because An initial estimate of +5 is wildly optimistic.
  C8.text：The initial action-value estimate is wildly optimistic at +5. because This optimism encourages action-value methods to explore.
- R2 核心：When the agent selects an action greedily based on the optimistic estimate, the actual reward received is lower than the current value estimate, so the learner is 'disappointed' with that action.
  判定：fail；No candidate describes the specific 'disappointment' mechanism: that when a greedy action is selected, the actual reward is lower than the current (optimistic) value estimate. Candidates mention optimism and exploration outcomes but not this gap or the resulting disappointment.
- R3 核心：Disappointment causes the estimated value of the chosen action to drop below the estimates of the other (still optimistic) actions, so the agent switches to trying other actions.
  判定：uncertain；C2 describes the outcome (all actions are tried under greedy selection) which logically implies a switching mechanism, but the specific causal chain (chosen action's value drops below the other still-optimistic estimates, causing a switch) is not explicitly stated in any candidate.
  C2.text：All actions are tried several times before the value estimates converge. as a result The system does a fair amount of exploration even if greedy actions are selected all the time.
- R4 核心：Consequently, all actions are tried several times before the value estimates converge, producing exploration even though actions are selected greedily.
  判定：pass；C2 directly states that all actions are tried several times before value estimates converge, and that this produces exploration even when greedy actions are selected all the time, matching R4's claim.
  C2.text：All actions are tried several times before the value estimates converge. as a result The system does a fair amount of exploration even if greedy actions are selected all the time.
- R5 完整答案补充：Illustrative example: in the 10-armed testbed, setting Q1(a) = +5 while q*(a) ~ N(0,1) makes +5 a wildly optimistic initial estimate, and the resulting technique is called 'optimistic initial values'.
  判定：pass；C1 names the technique 'optimistic initial values', C8 states the initial estimate is wildly optimistic at +5, and C10 states the initial values are +5 while true values are drawn from a distribution with mean 0, collectively covering the illustrative example. (The '10-armed testbed' label and explicit N(0,1) notation are not in the candidates, but the substantive content of the example is supported.)
  C1.text：optimistic initial values encourage exploration
  C8.text：The initial action-value estimate is wildly optimistic at +5.
  C10.text：The initial action values are set to +5 while the true values are drawn from a distribution with mean 0. because An initial estimate of +5 is wildly optimistic.

## GraphRAG / rl-qa-ch02-2

任务：t_37f4c1d44848ff6a5c4d6c41

How can optimistic initial action-value estimates encourage exploration even when actions are selected greedily?

旧：pass；核心：pass；完整：fail

- R1 核心：Optimistic initial action-value estimates are set higher than the true expected rewards, so the initial estimate for any action exceeds the rewards that action will actually yield.
  判定：pass；C1 states 'rewards are less than the initial estimates', which directly implies that the initial estimates are set higher than the true expected rewards, supporting the core claim.
  C1.text：rewards are less than the initial estimates so the learner switches actions
- R2 核心：When the agent selects an action greedily based on the optimistic estimate, the actual reward received is lower than the current value estimate, so the learner is 'disappointed' with that action.
  判定：pass；C1 explicitly names the 'disappointment mechanism' and states rewards are less than the initial estimates; C7 confirms this occurs even with greedy methods. Together they support the claim that greedy selection of an optimistically estimated action yields a lower actual reward, causing disappointment.
  C1.text：Optimistic initial values encourage exploration through the disappointment mechanism: rewards are less than the initial estimates so the learner switches actions
  C7.text：causes even greedy methods to explore significantly
- R3 核心：Disappointment causes the estimated value of the chosen action to drop below the estimates of the other (still optimistic) actions, so the agent switches to trying other actions.
  判定：pass；C1 describes that disappointment (rewards < estimates) causes the learner to switch actions, which logically requires the chosen action's updated estimate to fall below the other (still optimistic) actions. C2 reinforces by stating the learner is pushed to try all actions.
  C1.text：rewards are less than the initial estimates so the learner switches actions
  C2.text：pushing the learner to try all actions
- R4 核心：Consequently, all actions are tried several times before the value estimates converge, producing exploration even though actions are selected greedily.
  判定：pass；C2 states the learner is pushed to 'try all actions' and the technique encourages exploration; C5 confirms exploration happens 'even when the exploration parameter ε is zero'; C7 confirms greedy methods explore significantly. This collectively supports that all actions are tried before convergence, producing exploration under greedy selection.
  C2.text：Optimistic initial values encourage exploration by making initial rewards disappointing and pushing the learner to try all actions
  C5.text：Optimistic initialization of action values to zero drives extensive exploration even when the exploration parameter ε is zero
  C7.text：causes even greedy methods to explore significantly
- R5 完整答案补充：Illustrative example: in the 10-armed testbed, setting Q1(a) = +5 while q*(a) ~ N(0,1) makes +5 a wildly optimistic initial estimate, and the resulting technique is called 'optimistic initial values'.
  判定：fail；No candidate mentions the 10-armed testbed, the Q1(a) = +5 value, or the q*(a) ~ N(0,1) distribution. The specific illustrative example is entirely absent from the candidates.

## KGGen / rl-qa-ch02-2

任务：t_840c029aa8dd1edc11cc6318

How can optimistic initial action-value estimates encourage exploration even when actions are selected greedily?

旧：fail；核心：fail；完整：fail

- R1 核心：Optimistic initial action-value estimates are set higher than the true expected rewards, so the initial estimate for any action exceeds the rewards that action will actually yield.
  判定：fail；No candidate asserts that optimistic initial estimates are set higher than the true expected rewards or that the initial estimate exceeds the actual reward. C2 only says optimistic initial values 'focuses on initial estimates' and C10 only states Q1(a)=+5 is an initial value, without any comparison to true expected rewards.
  C10.text：Q1(a) = +5 is initial value for action-value estimates
- R2 核心：When the agent selects an action greedily based on the optimistic estimate, the actual reward received is lower than the current value estimate, so the learner is 'disappointed' with that action.
  判定：fail；No candidate describes that actual rewards received are lower than the current value estimate or that the learner is 'disappointed'. C3 and C4 mention greedy selection via the optimistic greedy method, but none address the discrepancy between received reward and estimate.
  C3.text：optimistic greedy method encourages exploration via optimistic initial values
- R3 核心：Disappointment causes the estimated value of the chosen action to drop below the estimates of the other (still optimistic) actions, so the agent switches to trying other actions.
  判定：fail；No candidate describes the mechanism where the chosen action's estimated value drops below other (still optimistic) estimates, causing the agent to switch. C6 mentions bias disappearing after all actions are selected, but does not describe the value-dropping or switching mechanism.
  C6.text：sample-average method have bias that disappears once all actions selected action-value estimates
- R4 核心：Consequently, all actions are tried several times before the value estimates converge, producing exploration even though actions are selected greedily.
  判定：fail；No candidate directly states that all actions are tried several times before value estimates converge, producing exploration under greedy selection. C6's mention of bias disappearing once all actions are selected is tangentially related but does not cover 'several times', 'before convergence', or the contradiction with greedy selection.
  C6.text：sample-average method have bias that disappears once all actions selected action-value estimates
- R5 完整答案补充：Illustrative example: in the 10-armed testbed, setting Q1(a) = +5 while q*(a) ~ N(0,1) makes +5 a wildly optimistic initial estimate, and the resulting technique is called 'optimistic initial values'.
  判定：fail；No candidate mentions the 10-armed testbed, the distribution q*(a) ~ N(0,1), or describes +5 as 'wildly optimistic'. C10 only states Q1(a)=+5 is an initial value for action-value estimates, without the illustrative example context.
  C10.text：Q1(a) = +5 is initial value for action-value estimates

## 我们的方法（强化学习） / rl-qa-ch02-2

任务：t_f26e623d90d45a7f65d4f8be

How can optimistic initial action-value estimates encourage exploration even when actions are selected greedily?

旧：fail；核心：fail；完整：fail

- R1 核心：Optimistic initial action-value estimates are set higher than the true expected rewards, so the initial estimate for any action exceeds the rewards that action will actually yield.
  判定：pass；C1 states that optimistic initialization sets all initial Q₁(a) to 'an optimistic value such as +5, rather than zero.' The term 'optimistic' inherently means higher than the true expected rewards, and setting them to +5 (rather than zero) supports that the initial estimate exceeds what the action will actually yield.
  C1.text：optimistic initialization（强化学习） sets all initial 初始动作价值估计 Q₁(a) to an optimistic value such as +5, rather than zero, as a simple way to encourage exploration through action-value methods.
- R2 核心：When the agent selects an action greedily based on the optimistic estimate, the actual reward received is lower than the current value estimate, so the learner is 'disappointed' with that action.
  判定：fail；No candidate describes the disappointment mechanism—that selecting greedily based on the optimistic estimate yields a lower actual reward than the current estimate. C1 only says it is 'a simple way to encourage exploration' without describing why the actual reward would be disappointing.
- R3 核心：Disappointment causes the estimated value of the chosen action to drop below the estimates of the other (still optimistic) actions, so the agent switches to trying other actions.
  判定：fail；No candidate describes the mechanism by which the chosen action's value drops below the other still-optimistic actions, causing the agent to switch. The candidates mention the technique encourages exploration but do not explain the switching mechanism.
- R4 核心：Consequently, all actions are tried several times before the value estimates converge, producing exploration even though actions are selected greedily.
  判定：uncertain；C1 and C9 say the technique encourages exploration through action-value methods, which implicitly involves greedy selection (as it is contrasted with ε-greedy in C8). However, no candidate explicitly states that 'all actions are tried several times before the value estimates converge' or that exploration happens 'even though actions are selected greedily.' The result is plausible from context but not directly stated.
  C1.text：optimistic initialization（强化学习） sets all initial 初始动作价值估计 Q₁(a) to an optimistic value such as +5, rather than zero, as a simple way to encourage exploration through action-value methods.
- R5 完整答案补充：Illustrative example: in the 10-armed testbed, setting Q1(a) = +5 while q*(a) ~ N(0,1) makes +5 a wildly optimistic initial estimate, and the resulting technique is called 'optimistic initial values'.
  判定：uncertain；C1 mentions 'optimistic value such as +5' and uses the term 'optimistic initialization', partially supporting the illustrative example. However, no candidate mentions the 10-armed testbed, q*(a) ~ N(0,1), or the alternative name 'optimistic initial values'.
  C1.text：optimistic initialization（强化学习） sets all initial 初始动作价值估计 Q₁(a) to an optimistic value such as +5, rather than zero, as a simple way to encourage exploration through action-value methods.

## AutoSchemaKG / rl-qa-ch03-1

任务：t_1e35dbfed2cbc816141085a8

In the simplest case, how is the return G_t defined in terms of the reward sequence, and what role does T play?

旧：fail；核心：fail；完整：fail

- R1 核心：In the simplest case, the return G_t is defined as the sum of the reward sequence.
  判定：uncertain；C6 states 'return defined as function of reward sequence', which is related to the idea that the return depends on the reward sequence, but does not specifically capture the 'sum' of the reward sequence as required. No candidate explicitly says G_t is defined as a sum.
  C6.text：return defined as function of reward sequence
- R2 核心：The formal expression is G_t = R_{t+1} + R_{t+2} + R_{t+3} + ... + R_T, summing the rewards received after time step t up through time step T.
  判定：fail；No candidate provides the formal expression G_t = R_{t+1} + R_{t+2} + R_{t+3} + ... + R_T or any equivalent summation formula. C9 references Gt and T but in the context of n-step returns, not the simplest case definition.
- R3 核心：T denotes a final time step, and the fact that the sum terminates at T makes this formulation appropriate for episodic tasks in which there is a natural notion of a final time step.
  判定：fail；No candidate explicitly states that T is a final time step making the formulation appropriate for episodic tasks. C5 mentions 'termination time T' but only in the context of the λ-return (not the simplest case). C9 mentions T in the context of n-step returns and termination conditions, but does not describe the episodic task context or the simplest case.

## GraphRAG / rl-qa-ch03-1

任务：t_691aa00d227af781f5158c10

In the simplest case, how is the return G_t defined in terms of the reward sequence, and what role does T play?

旧：pass；核心：uncertain；完整：uncertain

- R1 核心：In the simplest case, the return G_t is defined as the sum of the reward sequence.
  判定：pass；C1 directly states 'In the simplest case, the return Gt is defined as the sum of rewards, formalizing cumulative reward', which fully supports that the simplest-case return is defined as a sum of the reward sequence.
  C1.text：In the simplest case, the return Gt is defined as the sum of rewards, formalizing cumulative reward
- R2 核心：The formal expression is G_t = R_{t+1} + R_{t+2} + R_{t+3} + ... + R_T, summing the rewards received after time step t up through time step T.
  判定：uncertain；C3 gives the indexed form 'a sum of rewards R_{t+k+1}' (implying R_{t+1}, R_{t+2}, ...) and C9 confirms it 'starts at time t+1'. However, no candidate explicitly reproduces the full expansion G_t = R_{t+1} + R_{t+2} + ... + R_T, nor explicitly states that the sum runs up through time step T. The upper bound at T is not shown in any candidate text.
  C3.text：The return G_t is defined as a sum of rewards R_t+k+1 in equation (3.9)
  C9.text：The return is a specific function of the reward signal sequence starting at time t+1
- R3 核心：T denotes a final time step, and the fact that the sum terminates at T makes this formulation appropriate for episodic tasks in which there is a natural notion of a final time step.
  判定：uncertain；C5 states the full return 'is defined over an entire episode from t until termination', which covers the episodic-task framing and the idea that the sum terminates. However, no candidate explicitly identifies T as the notation for a final time step, nor explicitly links the termination to episodic tasks in those terms. The role of T as a final-time-step variable is only implicit.
  C5.text：The full return G_t is defined over an entire episode from t until termination

## KGGen / rl-qa-ch03-1

任务：t_3947cab0ffe6a7733343d2d2

In the simplest case, how is the return G_t defined in terms of the reward sequence, and what role does T play?

旧：fail；核心：fail；完整：fail

- R1 核心：In the simplest case, the return G_t is defined as the sum of the reward sequence.
  判定：fail；No candidate states that G_t is defined as the sum of the reward sequence in the simplest case. C1 only mentions a single immediate reward R_{t+1}, and C6 only references a cost/reward relationship (Ct = Rt), not a summation. C3 mentions a reward sequence is bounded for G_t but does not say G_t equals the sum of the sequence.
- R2 核心：The formal expression is G_t = R_{t+1} + R_{t+2} + R_{t+3} + ... + R_T, summing the rewards received after time step t up through time step T.
  判定：fail；No candidate provides the formal expression G_t = R_{t+1} + R_{t+2} + R_{t+3} + ... + R_T. C1 only references R_{t+1} in isolation and does not describe a summation from t+1 to T.
- R3 核心：T denotes a final time step, and the fact that the sum terminates at T makes this formulation appropriate for episodic tasks in which there is a natural notion of a final time step.
  判定：fail；No candidate discusses T as a final time step, nor mentions that the termination at T makes this formulation appropriate for episodic tasks with a natural final time step.

## 我们的方法（强化学习） / rl-qa-ch03-1

任务：t_eb435a0bcadeb91d035e90d3

In the simplest case, how is the return G_t defined in terms of the reward sequence, and what role does T play?

旧：fail；核心：fail；完整：fail

- R1 核心：In the simplest case, the return G_t is defined as the sum of the reward sequence.
  判定：fail；No candidate provides the simplest-case definition of G_t as the sum of the reward sequence. C1 and C3 define the differential return in the continuing case (with r(π) subtracted), not the standard undiscounted sum in the simplest case. C4 mentions 'conventional value functions were defined in terms of the discounted return,' which is not the simplest (undiscounted) case.
  C1.text：G_t = R_{t+1} − r(π) + R_{t+2} − r(π) + … (equation 13.17)
- R2 核心：The formal expression is G_t = R_{t+1} + R_{t+2} + R_{t+3} + ... + R_T, summing the rewards received after time step t up through time step T.
  判定：fail；No candidate provides the explicit formula G_t = R_{t+1} + R_{t+2} + R_{t+3} + … + R_T summing the rewards from t+1 through T. C1/C3 give a different formula (differential return with −r(π) terms, continuing case). C7 gives the λ-return as a weighted sum of n-step returns, not the simple reward sum. No candidate contains the required sum-of-rewards expression.
  C1.text：G_t = R_{t+1} − r(π) + R_{t+2} − r(π) + … (equation 13.17)
- R3 核心：T denotes a final time step, and the fact that the sum terminates at T makes this formulation appropriate for episodic tasks in which there is a natural notion of a final time step.
  判定：uncertain；C2 and C5 both support that T is a termination time: C2 states the n-step return equals the ordinary G_t when extending to/beyond 'termination,' and C5 explicitly calls T the 'time of termination' in the λ-return. However, no candidate explicitly states that the sum terminating at T makes this formulation appropriate for 'episodic tasks' — the connection between T-termination and the episodic setting is not directly asserted in the candidates.
  C2.text：When t + n ≥ T (i.e., the n-step return (reinforcement learning) extends to or beyond termination), the n-step return (reinforcement learning) is defined to be equal to the ordinary 回报（强化学习） G_t.
  C5.text：the horizon h plays the same role as the time of termination T plays in the λ-return (reinforcement learning) (equation 12.3)

## AutoSchemaKG / rl-qa-ch03-2

任务：t_4b90e7b4c7677cb7101444f7

Why is explicitly solving the Bellman optimality equation rarely directly useful for finding an optimal policy in practice?

旧：pass；核心：fail；完整：fail

- R1 核心：Explicitly solving the Bellman optimality equation is rarely directly useful because the approach relies on three assumptions that are rarely true in practice.
  判定：uncertain；C1 confirms 'rarely directly useful' and C3 states 'relies on three assumptions that are rarely true in practice' and 'This solution is rarely directly useful'. Both key facts are present, but C3's causal direction is reversed (it says 'relies on three assumptions BECAUSE rarely directly useful', whereas R1 requires the opposite: 'rarely directly useful BECAUSE relies on three assumptions'). Per instructions, the wrong direction cannot be self-corrected.
  C1.text：Explicitly solving the Bellman optimality equation is rarely directly useful for practical problems
  C3.subject：This solution relies on three assumptions that are rarely true in practice
  C3.object：This solution is rarely directly useful
- R2 核心：Assumption 1: the dynamics of the environment are accurately known.
  判定：fail；No candidate mentions dynamics of the environment or that they must be accurately known as an assumption.
- R3 核心：Assumption 2: computational resources are sufficient to complete the calculation.
  判定：fail；No candidate explicitly states that sufficient computational resources is one of the three assumptions. C1 and C4 only imply computational difficulty but do not frame it as the listed assumption.
- R4 核心：Assumption 3: the states have the Markov property.
  判定：fail；No candidate mentions the Markov property or that states having the Markov property is one of the assumptions.
- R5 完整答案补充：Illustrative example: backgammon has about 10^20 states, and solving the Bellman equation for v* would take thousands of years on today's fastest computers.
  判定：fail；No candidate mentions backgammon, 10^20 states, or thousands of years of computation. C4 mentions board games (chess) and computers but is not the specific backgammon illustrative example required.

## GraphRAG / rl-qa-ch03-2

任务：t_3a07b584b38e0df08d180302

Why is explicitly solving the Bellman optimality equation rarely directly useful for finding an optimal policy in practice?

旧：fail；核心：fail；完整：fail

- R1 核心：Explicitly solving the Bellman optimality equation is rarely directly useful because the approach relies on three assumptions that are rarely true in practice.
  判定：uncertain；C1 and C5 support two of the required assumptions (dynamics and Markov property), but no candidate mentions a third assumption about computational resources, and no candidate explicitly states the overarching claim that 'explicitly solving the Bellman optimality equation is rarely directly useful because it relies on three assumptions.' The full 'three assumptions' framing cannot be confirmed from the candidates alone.
  C1.text：Explicitly solving the Bellman optimality equation requires accurate knowledge of the environment's dynamics, which is rarely available
  C5.text：Explicitly solving the Bellman optimality equation requires the states to have the Markov property
- R2 核心：Assumption 1: the dynamics of the environment are accurately known.
  判定：pass；C1 directly states that explicitly solving the Bellman optimality equation requires accurate knowledge of the environment's dynamics, which is rarely available.
  C1.text：Explicitly solving the Bellman optimality equation requires accurate knowledge of the environment's dynamics, which is rarely available
- R3 核心：Assumption 2: computational resources are sufficient to complete the calculation.
  判定：fail；No candidate mentions computational resources being required or sufficient for explicitly solving the Bellman optimality equation. This assumption is entirely absent from the candidates.
- R4 核心：Assumption 3: the states have the Markov property.
  判定：pass；C5 directly states that explicitly solving the Bellman optimality equation requires the states to have the Markov property.
  C5.text：Explicitly solving the Bellman optimality equation requires the states to have the Markov property
- R5 完整答案补充：Illustrative example: backgammon has about 10^20 states, and solving the Bellman equation for v* would take thousands of years on today's fastest computers.
  判定：fail；C3 mentions chess, not backgammon, and does not provide the specific details about 10^20 states or thousands of years of computation time. The backgammon illustrative example is not supported by any candidate.
  C3.text：Chess is cited as an example where optimal moves cannot be computed by solving the Bellman optimality equation

## KGGen / rl-qa-ch03-2

任务：t_66cd463d01937d3c2ce80c42

Why is explicitly solving the Bellman optimality equation rarely directly useful for finding an optimal policy in practice?

旧：fail；核心：fail；完整：fail

- R1 核心：Explicitly solving the Bellman optimality equation is rarely directly useful because the approach relies on three assumptions that are rarely true in practice.
  判定：fail；No candidate mentions that explicitly solving the Bellman optimality equation relies on three assumptions that are rarely true in practice. Candidates only describe what the equation is/does.
- R2 核心：Assumption 1: the dynamics of the environment are accurately known.
  判定：fail；No candidate mentions the assumption that the dynamics of the environment must be accurately known.
- R3 核心：Assumption 2: computational resources are sufficient to complete the calculation.
  判定：fail；No candidate mentions the assumption that computational resources must be sufficient to complete the calculation.
- R4 核心：Assumption 3: the states have the Markov property.
  判定：fail；No candidate mentions the assumption that states must have the Markov property.
- R5 完整答案补充：Illustrative example: backgammon has about 10^20 states, and solving the Bellman equation for v* would take thousands of years on today's fastest computers.
  判定：fail；No candidate mentions the backgammon example with 10^20 states or the thousands-of-years computation estimate.

## 我们的方法（强化学习） / rl-qa-ch03-2

任务：t_5c9bed7413cf8f55aed61e9d

Why is explicitly solving the Bellman optimality equation rarely directly useful for finding an optimal policy in practice?

旧：fail；核心：fail；完整：fail

- R1 核心：Explicitly solving the Bellman optimality equation is rarely directly useful because the approach relies on three assumptions that are rarely true in practice.
  判定：fail；No candidate asserts that explicitly solving the Bellman optimality equation relies on three assumptions that are rarely true in practice. Candidates discuss related topics (dynamic programming, value iteration, Bellman error, etc.) but none address the reason given in this requirement.
- R2 核心：Assumption 1: the dynamics of the environment are accurately known.
  判定：fail；No candidate states that the approach assumes the dynamics of the environment are accurately known. C7 discusses learning environment models but does not state this as an assumption for solving the Bellman optimality equation. C10 mentions 'without a model' but does not assert that known dynamics is an assumption.
- R3 核心：Assumption 2: computational resources are sufficient to complete the calculation.
  判定：fail；No candidate states that the approach assumes computational resources are sufficient. C5 mentions 'considerable additional computation' in the context of checking for optimal policy emergence, not as a stated assumption for explicitly solving the Bellman optimality equation.
- R4 核心：Assumption 3: the states have the Markov property.
  判定：fail；No candidate states that the states having the Markov property is an assumption of explicitly solving the Bellman optimality equation. None of the candidates mention the Markov property at all.
- R5 完整答案补充：Illustrative example: backgammon has about 10^20 states, and solving the Bellman equation for v* would take thousands of years on today's fastest computers.
  判定：fail；No candidate mentions backgammon, 10^20 states, or thousands of years of computation. None of the candidates provide this illustrative example.

## AutoSchemaKG / rl-qa-ch04-1

任务：t_1f0c1e79dd8caf23a871c3d0

In policy improvement, what rule governs the apportionment of probability among actions when multiple actions tie at the maximum in the stochastic case?

旧：pass；核心：pass；完整：pass

- R1 核心：In the stochastic case, when multiple actions tie at the maximum in a policy improvement step, the new greedy policy need not select a single action—any apportioning scheme is permitted.
  判定：pass；C1 directly states that in the stochastic case we need not select a single action from among the maximizing actions and that apportioning among tied actions is allowed, matching the requirement that any apportioning scheme is permitted.
  C1.text：In the stochastic case, we need not select a single action from among the maximizing actions because If there are ties in policy improvement steps where several actions achieve the maximum, apportioning among them is allowed
- R2 核心：Each maximizing action can be given a portion of the probability of being selected in the new greedy policy.
  判定：pass；C1 explicitly says that when several actions tie at the maximum, 'apportioning among them is allowed,' which directly supports the requirement that each maximizing action can be given a portion of the selection probability.
  C1.text：apportioning among them is allowed
- R3 核心：All submaximal (non-maximizing) actions must be given zero probability.
  判定：pass；C2 states that a policy assigns nonzero probability only to actions at which the maximum is obtained, which directly implies that all submaximal (non-maximizing) actions must be given zero probability.
  C2.text：A policy assigns nonzero probability only to actions at which the maximum is obtained in the Bellman optimality equation.

## GraphRAG / rl-qa-ch04-1

任务：t_f91e5b3152d38e8ee3a23cdc

In policy improvement, what rule governs the apportionment of probability among actions when multiple actions tie at the maximum in the stochastic case?

旧：fail；核心：fail；完整：fail

- R1 核心：In the stochastic case, when multiple actions tie at the maximum in a policy improvement step, the new greedy policy need not select a single action—any apportioning scheme is permitted.
  判定：uncertain；C2 states that 'the argmax operation breaks ties arbitrarily,' which partially aligns with the idea that any apportioning scheme is permitted, but C2 discusses the argmax operation generally rather than specifically addressing policy improvement in the stochastic case or probability apportionment among maximizing actions. The connection is suggestive but not definitive.
  C2.text：When multiple actions attain the maximum, the argmax operation breaks ties arbitrarily
- R2 核心：Each maximizing action can be given a portion of the probability of being selected in the new greedy policy.
  判定：fail；No candidate explicitly states that each maximizing action can be given a portion of the probability of being selected. C1 mentions 'randomly selects among them' (implying single-action selection), and C3 describes stochastic policies generally but does not address apportionment among tied maximizing actions.
- R3 核心：All submaximal (non-maximizing) actions must be given zero probability.
  判定：fail；No candidate states that submaximal (non-maximizing) actions must be given zero probability. The candidates discuss tie-breaking among max actions or general policy properties, but none address the zero-probability requirement for non-maximizing actions.

## KGGen / rl-qa-ch04-1

任务：t_abd530ad334fe356fd6adefc

In policy improvement, what rule governs the apportionment of probability among actions when multiple actions tie at the maximum in the stochastic case?

旧：pass；核心：fail；完整：fail

- R1 核心：In the stochastic case, when multiple actions tie at the maximum in a policy improvement step, the new greedy policy need not select a single action—any apportioning scheme is permitted.
  判定：uncertain；C1 mentions 'maximizing actions apportion probability among stochastic policies' which loosely suggests probability distribution among maximizers, and C2 acknowledges ties exist in policy improvement steps. However, neither candidate explicitly states that 'any' apportioning scheme is permitted, nor do they address the greedy policy's behavior when ties occur. The support is suggestive but ambiguous.
  C1.text：maximizing actions apportion probability among stochastic policies
  C2.text：maximizing actions may contain ties among policy improvement steps (4.9)
- R2 核心：Each maximizing action can be given a portion of the probability of being selected in the new greedy policy.
  判定：pass；C1 states that maximizing actions apportion probability among stochastic policies, which supports the idea that each maximizing action can be given a portion of the probability.
  C1.text：maximizing actions apportion probability among stochastic policies
- R3 核心：All submaximal (non-maximizing) actions must be given zero probability.
  判定：fail；No candidate assertion mentions submaximal or non-maximizing actions, nor states that such actions must be assigned zero probability. This required content is entirely absent from the candidates.

## 我们的方法（强化学习） / rl-qa-ch04-1

任务：t_4163cbfa0369fd76c04c8d21

In policy improvement, what rule governs the apportionment of probability among actions when multiple actions tie at the maximum in the stochastic case?

旧：pass；核心：pass；完整：pass

- R1 核心：In the stochastic case, when multiple actions tie at the maximum in a policy improvement step, the new greedy policy need not select a single action—any apportioning scheme is permitted.
  判定：pass；C1 explicitly states that in the stochastic case when there are ties among the maximizing actions, probability is 'apportioned among all maximizing actions,' indicating any apportioning scheme is permitted and a single action need not be selected.
  C1.text：In the stochastic case, a 贪心策略（强化学习） can be implemented as a 随机策略（强化学习）, with probability apportioned among all maximizing actions while giving zero probability to all submaximal actions.
  C1.scope：in the stochastic case, when there are ties among the maximizing actions in the argmax
- R2 核心：Each maximizing action can be given a portion of the probability of being selected in the new greedy policy.
  判定：pass；C1 directly states that probability is 'apportioned among all maximizing actions,' meaning each maximizing action can receive a portion of the probability.
  C1.text：with probability apportioned among all maximizing actions while giving zero probability to all submaximal actions.
- R3 核心：All submaximal (non-maximizing) actions must be given zero probability.
  判定：pass；C1 explicitly states 'giving zero probability to all submaximal actions,' directly supporting that non-maximizing actions must be given zero probability.
  C1.text：with probability apportioned among all maximizing actions while giving zero probability to all submaximal actions.

## AutoSchemaKG / rl-qa-ch04-2

任务：t_b8b50646c0f5641a28596207

Why does policy iteration on a finite Markov decision process converge to an optimal policy in a finite number of iterations, and what is the relationship between successive policies in the sequence?

旧：pass；核心：pass；完整：pass

- R1 核心：Each policy in the iteration sequence is guaranteed to be a strict improvement over the previous policy (unless that previous policy is already optimal), so the policies form a monotonically improving sequence.
  判定：pass；C2 directly states that 'A sequence of monotonically improving policies and value functions is obtained' through policy iteration, supporting the claim that successive policies form a monotonically improving sequence.
  C2.object：A sequence of monotonically improving policies and value functions is obtained
- R2 核心：A finite MDP has only a finite number of deterministic policies, so this strictly improving sequence cannot continue indefinitely and must reach an optimal policy in a finite number of iterations.
  判定：pass；C1 directly states the full reasoning: 'This process must converge to an optimal policy and the optimal value function in a finite number of iterations because A finite MDP has only a finite number of deterministic policies', which exactly matches the requirement.
  C1.text：This process must converge to an optimal policy and the optimal value function in a finite number of iterations because A finite MDP has only a finite number of deterministic policies
- R3 完整答案补充：The value functions produced alongside the policies are also monotonically improving, and the process converges to the optimal value function as well as the optimal policy.
  判定：pass；C2 supports the monotonically improving value functions ('monotonically improving policies and value functions'), and C1 supports convergence to the optimal value function ('converge to an optimal policy and the optimal value function'). Together they cover all elements of this requirement.
  C2.object：A sequence of monotonically improving policies and value functions is obtained
  C1.text：This process must converge to an optimal policy and the optimal value function in a finite number of iterations

## GraphRAG / rl-qa-ch04-2

任务：t_47b0af0d3fa10fb147c4a417

Why does policy iteration on a finite Markov decision process converge to an optimal policy in a finite number of iterations, and what is the relationship between successive policies in the sequence?

旧：uncertain；核心：pass；完整：fail

- R1 核心：Each policy in the iteration sequence is guaranteed to be a strict improvement over the previous policy (unless that previous policy is already optimal), so the policies form a monotonically improving sequence.
  判定：pass；C1 explicitly states that policy iteration works 'through a process of successive policy improvements' and 'gradually refining the policy with each iteration until it eventually finds the optimal policy.' The term 'successive policy improvements' conveys strict improvement at each step, and 'until it eventually finds the optimal policy' conveys the conditional stopping condition (no further improvement when optimal is reached).
  C1.text：converges to the optimal policy π* through a process of successive policy improvements
  C1.text：iteratively alternates between two main steps—policy evaluation and policy improvement—gradually refining the policy with each iteration until it eventually finds the optimal policy
- R2 核心：A finite MDP has only a finite number of deterministic policies, so this strictly improving sequence cannot continue indefinitely and must reach an optimal policy in a finite number of iterations.
  判定：pass；C5 establishes that a finite MDP has finite state, action, and reward sets; from finite state and action sets it is a direct semantic inference that the number of deterministic policies is also finite. C1 establishes that the algorithm produces 'successive policy improvements' (strict improvements) and 'eventually finds the optimal policy.' Combining these: finitely many deterministic policies + strictly improving sequence → the sequence must terminate at an optimal policy in a finite number of iterations. C9 further supports the existence of an optimal policy for finite MDPs.
  C5.text：A finite MDP is an MDP with finite state, action, and reward sets
  C1.text：converges to the optimal policy π* through a process of successive policy improvements
  C1.text：gradually refining the policy with each iteration until it eventually finds the optimal policy
  C9.text：for every finite MDP, there is always at least one optimal policy available
- R3 完整答案补充：The value functions produced alongside the policies are also monotonically improving, and the process converges to the optimal value function as well as the optimal policy.
  判定：fail；C1 states that policy iteration 'is guaranteed to converge to both the optimal policy and the corresponding optimal value function,' which partially supports the convergence claim. However, no candidate asserts that the value functions produced at each iteration are monotonically improving. This key component of R3 (monotonic improvement of intermediate value functions) is entirely absent from the candidates.
  C1.text：The policy iteration process is guaranteed to converge to both the optimal policy and the corresponding optimal value function

## KGGen / rl-qa-ch04-2

任务：t_f61195c8b0acd6793898c567

Why does policy iteration on a finite Markov decision process converge to an optimal policy in a finite number of iterations, and what is the relationship between successive policies in the sequence?

旧：fail；核心：fail；完整：fail

- R1 核心：Each policy in the iteration sequence is guaranteed to be a strict improvement over the previous policy (unless that previous policy is already optimal), so the policies form a monotonically improving sequence.
  判定：fail；No candidate asserts that successive policies are strict improvements or that the sequence is monotonically improving. C1 only states finite convergence without any mechanism about policy improvement.
- R2 核心：A finite MDP has only a finite number of deterministic policies, so this strictly improving sequence cannot continue indefinitely and must reach an optimal policy in a finite number of iterations.
  判定：fail；No candidate provides the key reasoning: that a finite MDP has a finite number of deterministic policies, which forces the strictly improving sequence to terminate in finite iterations. C1 only states the conclusion ('converges in finite iterations') without the underlying justification (finite policy space) required by the question's 'why'.
  C1.text：simple finite MDP converges in finite iterations on Policy Iteration
- R3 完整答案补充：The value functions produced alongside the policies are also monotonically improving, and the process converges to the optimal value function as well as the optimal policy.
  判定：fail；No candidate asserts that value functions produced during policy iteration are monotonically improving or that the process converges to the optimal value function. C2 discusses value iteration (not policy iteration) and its infinite-iteration requirement, which is not the same claim.

## 我们的方法（强化学习） / rl-qa-ch04-2

任务：t_df365526a40f0e4d004e88b2

Why does policy iteration on a finite Markov decision process converge to an optimal policy in a finite number of iterations, and what is the relationship between successive policies in the sequence?

旧：fail；核心：fail；完整：fail

- R1 核心：Each policy in the iteration sequence is guaranteed to be a strict improvement over the previous policy (unless that previous policy is already optimal), so the policies form a monotonically improving sequence.
  判定：pass；C1 explicitly states that in the sequence of policies produced by policy iteration, 'each successive policy is a strict improvement over the previous policy, and the last policy in the sequence is the optimal policy.' This directly supports the claim of a monotonically improving sequence.
  C1.text：each successive policy is a strict improvement over the previous policy, and the last policy in the sequence is the optimal policy.
- R2 核心：A finite MDP has only a finite number of deterministic policies, so this strictly improving sequence cannot continue indefinitely and must reach an optimal policy in a finite number of iterations.
  判定：fail；The key mechanism—that a finite MDP has only a finite number of deterministic policies, so the strictly improving sequence cannot continue indefinitely—is not stated in any candidate. C1 confirms the sequence reaches an optimal policy but does not explain why in finite iterations (no mention of the finiteness of the number of deterministic policies). C5 mentions finite MDPs but only that optimal policies can be computed, not the counting argument.
- R3 完整答案补充：The value functions produced alongside the policies are also monotonically improving, and the process converges to the optimal value function as well as the optimal policy.
  判定：fail；No candidate asserts that the value functions are monotonically improving. C4 mentions 'the final state-value function' being displayed, and C5 mentions computing 'optimal policies and value functions,' but neither states that intermediate value functions are monotonically non-decreasing or that the process converges to the optimal value function alongside the optimal policy.

## AutoSchemaKG / rl-qa-ch05-1

任务：t_0024cad0f1ed82e5d4255792

In the 100-step importance-sampling example where the return is determined by the first reward alone, why do the importance-sampling factors after the first add variance without changing the expected update?

旧：pass；核心：pass；完整：pass

- R1 核心：在 γ=0 的 100 步示例中，return G0 仅由第一个奖励 R1 决定，因此第一步之后的 99 个重要性采样因子与已经确定的 return 相互独立。
  判定：pass；C1 directly states that after the first reward the return has already been determined, and that the later factors are independent of the return.
  C1.text：The other 99 factors are irrelevant because after the first reward the return has already been determined. as a result These later factors are independent of the return and add enormously to the variance, and in some cases they could even make the variance infinite.
- R2 核心：这 99 个后续因子中每一个的期望值都等于 1，因此将它们纳入乘积不会改变更新方向的期望值。
  判定：pass；C4 directly states that the expected value of all factors other than the first importance-sampling ratio is one, and that all other factors have no effect in expectation.
  C4.text：The expected value of all factors other than the first importance-sampling ratio is one as a result All other factors have no effect in expectation
- R3 核心：尽管这些因子保持期望不变（不影响期望更新），它们会给估计量带来巨大的方差，在某些情况下甚至使方差变为无穷大。
  判定：pass；C1 directly states that these later factors add enormously to the variance and in some cases could make the variance infinite. C6 and C8 provide additional supporting evidence about variance increase and infinite variance.
  C1.text：These later factors are independent of the return and add enormously to the variance, and in some cases they could even make the variance infinite.
  C6.text：extraneous importance-sampling factors increase variance
  C8.text：The simple calculation verifies that the expected square of the importance-sampling-scaled return is infinite as a result The variance of the importance-sampling-scaled returns is confirmed to be infinite

## GraphRAG / rl-qa-ch05-1

任务：t_d200225083462777d19c5058

In the 100-step importance-sampling example where the return is determined by the first reward alone, why do the importance-sampling factors after the first add variance without changing the expected update?

旧：pass；核心：fail；完整：fail

- R1 核心：在 γ=0 的 100 步示例中，return G0 仅由第一个奖励 R1 决定，因此第一步之后的 99 个重要性采样因子与已经确定的 return 相互独立。
  判定：pass；C3 直接描述了 100 步回合、重要性采样比率为 100 个因子的乘积，以及 γ=0 时仅第一个因子 relevant（'only the first is relevant when gamma = 0'），由此可推知 return 仅由 R1 决定，后 99 个因子不影响 return（即与已确定的 return 独立）。
  C3.text：For an episode of length 100, the importance sampling ratio is a product of 100 factors, but only the first is relevant when gamma = 0
- R2 核心：这 99 个后续因子中每一个的期望值都等于 1，因此将它们纳入乘积不会改变更新方向的期望值。
  判定：fail；没有任何候选断言明确说明后续 99 个重要性采样因子中每一个的期望值等于 1，也没有候选说明将这些因子纳入乘积不会改变更新方向的期望值。C5 讨论的是 baseline（基线）保持期望不变，并非重要性采样因子本身的期望性质；C8 提到单步重要性采样比 ρ_t，但未说明其期望为 1。
- R3 核心：尽管这些因子保持期望不变（不影响期望更新），它们会给估计量带来巨大的方差，在某些情况下甚至使方差变为无穷大。
  判定：pass；C2 明确指出 'the 99 later factors in the importance sampling ratio add enormously to the variance of the estimator'，直接对应 R3 中后续因子带来巨大方差的论断；C4 和 C6 进一步支持方差可以变为无穷（'The variance of importance-sampling-scaled returns is infinite'；'Ordinary importance sampling has infinite variance in Example 5.5'）。C1 和 C7 也提供一般性支持。
  C2.text：When the episode is long and gamma is small, the 99 later factors in the importance sampling ratio add enormously to the variance of the estimator
  C4.text：The variance of importance-sampling-scaled returns is infinite because the expected square of the scaled return diverges
  C6.text：Ordinary importance sampling has infinite variance in Example 5.5

## KGGen / rl-qa-ch05-1

任务：t_0af6a8ceabdca3197fcd069d

In the 100-step importance-sampling example where the return is determined by the first reward alone, why do the importance-sampling factors after the first add variance without changing the expected update?

旧：uncertain；核心：fail；完整：fail

- R1 核心：在 γ=0 的 100 步示例中，return G0 仅由第一个奖励 R1 决定，因此第一步之后的 99 个重要性采样因子与已经确定的 return 相互独立。
  判定：fail；没有任何候选提及 γ=0 的 100 步示例、G0 仅由 R1 决定、或第一步之后的 99 个因子与已确定 return 之间的独立性。候选中虽涉及 n-step 截断（C3, C7, C10），但均未具体描述 γ=0 情形下 return 由首个奖励唯一决定及后续因子与 return 独立的机制。
- R2 核心：这 99 个后续因子中每一个的期望值都等于 1，因此将它们纳入乘积不会改变更新方向的期望值。
  判定：uncertain；C4 提到 'importance-sampling ratio is 1 for factors in expected value'，可在宽松解读下支持每个因子的期望值为 1，但表述含糊且未明确指 99 个后续因子，也未说明纳入乘积不改变更新方向期望值。C5 反而说期望值等于 ρ 而非 1，与 R2 矛盾。证据不足以确认 R2 全部要点。
  C4.text：importance-sampling ratio is 1 for factors in expected value
- R3 核心：尽管这些因子保持期望不变（不影响期望更新），它们会给估计量带来巨大的方差，在某些情况下甚至使方差变为无穷大。
  判定：uncertain；C1 提到因子增加方差（variance），C2 提到因子可使方差变为无穷大，部分覆盖 R3 的方差增大和无穷方差主张。但两者的主语是 'importance-sampling ratio' 本身而非估计量的方差，且未提及'尽管期望不变'这一对照逻辑，表述模糊、不能确定完整支持 R3。
  C1.text：importance-sampling ratio is increased by factors in variance
  C2.text：importance-sampling ratio could be made infinite by factors in variance

## 我们的方法（强化学习） / rl-qa-ch05-1

任务：t_9cf4fbd6854789e22ba47971

In the 100-step importance-sampling example where the return is determined by the first reward alone, why do the importance-sampling factors after the first add variance without changing the expected update?

旧：uncertain；核心：fail；完整：fail

- R1 核心：在 γ=0 的 100 步示例中，return G0 仅由第一个奖励 R1 决定，因此第一步之后的 99 个重要性采样因子与已经确定的 return 相互独立。
  判定：pass；C1 directly supports that 'after the first reward the return has already been determined' and that only the first factor is really necessary, which implies subsequent factors are independent of the now-fixed return. Although C1 speaks of a general case ('episodes are long and γ is significantly less than 1') rather than naming the specific γ=0, 100-step example, the core mechanism required by R1 is covered.
  C1.text：when episodes are long and γ is significantly less than 1, only the first factor is really necessary because after the first reward the return has already been determined.
- R2 核心：这 99 个后续因子中每一个的期望值都等于 1，因此将它们纳入乘积不会改变更新方向的期望值。
  判定：pass；C3 states that 'the importance sampling ratio has expected value one,' which is the key property needed to conclude that multiplying the update by additional such factors (each with expected value 1) does not change the expected update. C3 does not mention the specific 100-step example, but the general property applies to each of the 99 subsequent factors.
  C3.text：the importance sampling ratio has expected value one and is uncorrelated with the estimate, so the expected value of the control variate is zero.
- R3 核心：尽管这些因子保持期望不变（不影响期望更新），它们会给估计量带来巨大的方差，在某些情况下甚至使方差变为无穷大。
  判定：fail；None of the candidate assertions mention the variance-inflating effect of multiplying by many importance sampling ratios, nor the possibility of infinite variance. The required content is absent from all candidates.

## AutoSchemaKG / rl-qa-ch05-2

任务：t_51baafddcd004318b09a0711

Does a consistent per-decision version of weighted importance sampling exist according to the authors?

旧：pass；核心：pass；完整：pass

- R1 核心：No, a consistent per-decision version of weighted importance sampling does not exist according to the authors.
  判定：pass；C1 states it is unclear if a per-decision version of weighted importance sampling exists, and C2 states weighted importance sampling lacks a per-decision version. The reason given (C1's object) is that all proposed estimators are not consistent, which effectively supports the conclusion that no consistent per-decision version exists.
  C1.subject：It is unclear if there is a per-decision version of weighted importance sampling
  C2.text：weighted importance sampling lacks per-decision version
- R2 核心：All per-decision weighted importance sampling estimators proposed so far are not consistent, meaning they do not converge to the true value even with infinite data.
  判定：pass；C1 directly states that all proposed per-decision weighted importance sampling estimators are not consistent and do not converge to the true value with infinite data, which matches R2 exactly.
  C1.text：All proposed per-decision weighted importance sampling estimators are not consistent and do not converge to the true value with infinite data

## GraphRAG / rl-qa-ch05-2

任务：t_ecd45884cb77120009f5d1b8

Does a consistent per-decision version of weighted importance sampling exist according to the authors?

旧：pass；核心：pass；完整：pass

- R1 核心：No, a consistent per-decision version of weighted importance sampling does not exist according to the authors.
  判定：pass；C2 explicitly states that no known per-decision versions of weighted importance sampling are consistent, directly supporting the claim that a consistent per-decision version does not exist.
  C2.text：No known per-decision versions of weighted importance sampling are consistent estimators
- R2 核心：All per-decision weighted importance sampling estimators proposed so far are not consistent, meaning they do not converge to the true value even with infinite data.
  判定：pass；C2 states that no known per-decision versions of weighted importance sampling are consistent estimators, which in statistical terms means they do not converge to the true value even with infinite data. This supports the claim that all per-decision weighted importance sampling estimators proposed so far are not consistent.
  C2.text：No known per-decision versions of weighted importance sampling are consistent estimators

## KGGen / rl-qa-ch05-2

任务：t_fa3c624419e4eb4ecab4a5f8

Does a consistent per-decision version of weighted importance sampling exist according to the authors?

旧：pass；核心：pass；完整：pass

- R1 核心：No, a consistent per-decision version of weighted importance sampling does not exist according to the authors.
  判定：pass；C8 directly states that the per-decision importance sampling estimator lacks estimator consistency, which supports the claim that no consistent per-decision version of weighted importance sampling exists.
  C8.text：per-decision importance sampling estimator lacks estimator consistency
- R2 核心：All per-decision weighted importance sampling estimators proposed so far are not consistent, meaning they do not converge to the true value even with infinite data.
  判定：pass；C8 states the per-decision importance sampling estimator lacks consistency, which in the statistical sense means the estimators do not converge to the true value even with infinite data. The 'all proposed so far' claim is supported by the general statement about per-decision importance sampling estimators lacking consistency.
  C8.text：per-decision importance sampling estimator lacks estimator consistency

## 我们的方法（强化学习） / rl-qa-ch05-2

任务：t_671c204d02f4a79d544c263f

Does a consistent per-decision version of weighted importance sampling exist according to the authors?

旧：pass；核心：pass；完整：pass

- R1 核心：No, a consistent per-decision version of weighted importance sampling does not exist according to the authors.
  判定：pass；C1 directly states that per-decision importance sampling has 'no known consistent weighted counterpart of weighted importance sampling,' which supports the claim that a consistent per-decision version of weighted importance sampling does not exist.
  C1.text：Per-decision importance sampling has no known consistent weighted counterpart of 加权重要性采样（强化学习）
- R2 核心：All per-decision weighted importance sampling estimators proposed so far are not consistent, meaning they do not converge to the true value even with infinite data.
  判定：pass；C1 explicitly states that 'all proposed per-decision versions of weighted importance sampling are not consistent (do not converge to the true value with infinite data),' which directly supports the claim that all proposed per-decision weighted importance sampling estimators are not consistent.
  C1.text：all proposed per-decision versions of 加权重要性采样（强化学习） are not consistent (do not converge to the true value with infinite data)

## AutoSchemaKG / rl-qa-ch06-1

任务：t_61306fd5122773d595ed8bfa

How is Expected Sarsa related to Q-learning when the target policy and behavior policy differ?

旧：pass；核心：pass；完整：fail

- R1 核心：When the target policy π is the greedy policy and the behavior policy is more exploratory, Expected Sarsa is exactly Q-learning.
  判定：pass；C1 directly states that when the target policy is the greedy policy and the behavior policy is more exploratory, Expected Sarsa is exactly Q-learning.
  C1.text：The target policy π is the greedy policy while the behavior policy is more exploratory. as a result Expected Sarsa is exactly Q-learning.
- R2 完整答案补充：In this sense, Expected Sarsa subsumes and generalizes Q-learning (since it can operate with target and behavior policies that differ, and reduces to Q-learning as a special case).
  判定：pass；Multiple candidates together support that Expected Sarsa subsumes/generalizes Q-learning and can operate with different target and behavior policies: C9 states Q-learning is a special case of Expected Sarsa, C3 states Expected Sarsa can use a policy different from the target policy, and C7/C10 state Q-learning generalizes to Expected Sarsa.
  C9.text：Q-learning is special case of Expected Sarsa
  C3.text：Expected Sarsa uses a policy different from the target policy π to generate behavior.
  C10.text：Tabular Q-learning generalizes to Expected Sarsa
- R3 完整答案补充：Expected Sarsa reliably improves over Sarsa, and aside from a small additional computational cost, it may dominate both Sarsa and Q-learning.
  判定：fail；No candidate mentions Expected Sarsa improving over Sarsa, small additional computational cost, or dominating both Sarsa and Q-learning.

## GraphRAG / rl-qa-ch06-1

任务：t_2ddf08b4760c8371c714834e

How is Expected Sarsa related to Q-learning when the target policy and behavior policy differ?

旧：pass；核心：pass；完整：fail

- R1 核心：When the target policy π is the greedy policy and the behavior policy is more exploratory, Expected Sarsa is exactly Q-learning.
  判定：pass；C2 explicitly states that Expected Sarsa 'reduces exactly to Q-learning when a greedy target policy is paired with exploratory behavior,' and C6 reinforces that 'Expected Sarsa can be used with an exploratory behavior policy, becoming Q-learning.' Together they directly support the claim.
  C2.text：Expected Sarsa subsumes and generalizes Q-learning, as it reduces exactly to Q-learning when a greedy target policy is paired with exploratory behavior.
  C6.text：Expected Sarsa can be used with an exploratory behavior policy, becoming Q-learning
- R2 完整答案补充：In this sense, Expected Sarsa subsumes and generalizes Q-learning (since it can operate with target and behavior policies that differ, and reduces to Q-learning as a special case).
  判定：pass；C2 directly asserts that 'Expected Sarsa subsumes and generalizes Q-learning' with the greedy target + exploratory behavior reduction. C1 supports the 'target and behavior policies may differ' aspect: 'the name now refers to the general algorithm where target and behavior policies may differ.' C5 adds that 'Expected Sarsa generalizes Q-learning to arbitrary target policies.'
  C2.text：Expected Sarsa subsumes and generalizes Q-learning, as it reduces exactly to Q-learning when a greedy target policy is paired with exploratory behavior.
  C1.text：the name now refers to the general algorithm where target and behavior policies may differ
  C5.text：Expected Sarsa generalizes Q-learning to arbitrary target policies, unifying the on-policy and off-policy perspectives of temporal-difference learning.
- R3 完整答案补充：Expected Sarsa reliably improves over Sarsa, and aside from a small additional computational cost, it may dominate both Sarsa and Q-learning.
  判定：fail；No candidate asserts that Expected Sarsa reliably improves over Sarsa, mentions a small additional computational cost, or claims it may dominate both Sarsa and Q-learning. C2 mentions outperforming Q-learning on the cliff walking task and behaving comparably for small learning rates, but these do not support the specific claims about Sarsa improvement, computational cost, or dominating both algorithms.
  C2.text：Expected Sarsa behaves comparably to Q-learning for small learning rates (α), and significantly outperforms Q-learning on the cliff walking task.

## KGGen / rl-qa-ch06-1

任务：t_b31c2bd9612d75e278581e5c

How is Expected Sarsa related to Q-learning when the target policy and behavior policy differ?

旧：pass；核心：fail；完整：fail

- R1 核心：When the target policy π is the greedy policy and the behavior policy is more exploratory, Expected Sarsa is exactly Q-learning.
  判定：fail；The requirement needs three components: (1) target policy π is greedy, (2) behavior policy is more exploratory, (3) Expected Sarsa is exactly Q-learning. While C5 states 'Q-learning is equivalent to Expected Sarsa' and C7 says 'van Hasselt (2011) called the off-policy Expected Sarsa is the name Q-learning', none of the candidates mention the specific conditions of a greedy target policy or an exploratory behavior policy. The conditional statement is not fully supported.
  C5.text：Q-learning is equivalent to Expected Sarsa
  C7.text：van Hasselt (2011) called the off-policy Expected Sarsa is the name Q-learning
- R2 完整答案补充：In this sense, Expected Sarsa subsumes and generalizes Q-learning (since it can operate with target and behavior policies that differ, and reduces to Q-learning as a special case).
  判定：pass；C9 directly states 'Expected Sarsa subsumes and generalizes Q-learning', matching the core claim. C3 supports that Expected Sarsa operates with a different target policy (off-policy capability). C10 additionally supports that Expected Sarsa includes Q-learning as an off-policy version. Together these cover subsumption, generalization, operation with differing policies, and inclusion of Q-learning.
  C9.text：Expected Sarsa subsumes and generalizes Q-learning
  C3.text：Expected Sarsa is described as off-policy algorithm when using different target policy (π)
  C10.text：Expected Sarsa is off-policy version including Q-learning
- R3 完整答案补充：Expected Sarsa reliably improves over Sarsa, and aside from a small additional computational cost, it may dominate both Sarsa and Q-learning.
  判定：fail；The requirement needs: (1) Expected Sarsa reliably improves over Sarsa, (2) small additional computational cost, (3) may dominate both Sarsa and Q-learning. None of the candidate assertions mention comparison to Sarsa, computational cost, or dominance. All candidates focus on the relationship between Expected Sarsa and Q-learning, not Sarsa comparisons.

## 我们的方法（强化学习） / rl-qa-ch06-1

任务：t_9eb9e9b475c79b63ff5a09a9

How is Expected Sarsa related to Q-learning when the target policy and behavior policy differ?

旧：pass；核心：pass；完整：fail

- R1 核心：When the target policy π is the greedy policy and the behavior policy is more exploratory, Expected Sarsa is exactly Q-learning.
  判定：pass；C1 directly states that when the target policy π is the greedy policy and the behavior policy is more exploratory, Expected Sarsa is exactly Q-learning.
  C1.text：If the target policy π is the greedy policy while the behavior policy is more exploratory, then Expected Sarsa is exactly Q学习.
- R2 完整答案补充：In this sense, Expected Sarsa subsumes and generalizes Q-learning (since it can operate with target and behavior policies that differ, and reduces to Q-learning as a special case).
  判定：pass；C9 directly states 'Expected Sarsa subsumes and generalizes Q学习.' C6 confirms Q-learning naturally generalizes to Expected Sarsa. C2 confirms Expected Sarsa can operate with different target and behavior policies (becoming an off-policy method). C1 confirms the special case reduction to Q-learning.
  C9.text：Expected Sarsa subsumes and generalizes Q学习.
  C2.text：In general, if Expected Sarsa uses a policy different from the target policy π to generate behavior, then Expected Sarsa becomes an 离策略方法（强化学习）.
- R3 完整答案补充：Expected Sarsa reliably improves over Sarsa, and aside from a small additional computational cost, it may dominate both Sarsa and Q-learning.
  判定：fail；No candidate assertion mentions Expected Sarsa improving over Sarsa, its computational cost relative to Sarsa/Q-learning, or that it may dominate both algorithms.

## AutoSchemaKG / rl-qa-ch06-2

任务：t_212b8ddefd6777df1c863f45

In the bandit discussion of maximization bias, what problem arises when the same noisy samples are used both to select the maximizing action and to estimate its value?

旧：pass；核心：pass；完整：pass

- R1 核心：Using the same samples both to select the maximizing action and to estimate its value produces a positive maximization bias.
  判定：pass；C1 directly states that maximization bias is caused by using the same samples to determine and estimate, and C10 confirms the bias is positive ('maximum of the estimates is positive when the true maximum is zero'). Together they cover the full requirement.
  C1.text：maximization bias caused by using same samples to determine and estimate
  C10.text：The maximum of the estimates is positive when the true maximum is zero. because The authors call this phenomenon maximization bias.
- R2 核心：As a result, the maximum of the noisy action-value estimates overestimates the maximum of the true action values.
  判定：pass；C10 directly describes the overestimation: the maximum of the noisy estimates is positive (above zero) while the true maximum is zero, meaning the estimated maximum overestimates the true maximum.
  C10.text：The maximum of the estimates is positive when the true maximum is zero.

## GraphRAG / rl-qa-ch06-2

任务：t_3a76e9c92e2d2fd6a30f3436

In the bandit discussion of maximization bias, what problem arises when the same noisy samples are used both to select the maximizing action and to estimate its value?

旧：pass；核心：pass；完整：pass

- R1 核心：Using the same samples both to select the maximizing action and to estimate its value produces a positive maximization bias.
  判定：pass；C5 identifies that the maximization bias arises specifically from 'using the same estimate both to select an action and to evaluate it', which matches the question's scenario. C7 confirms the resulting bias is a 'positive maximization bias'. C3 further characterizes it as 'biased upward', consistent with a positive bias.
  C5.text：the maximization bias that arises from using the same estimate both to select an action and to evaluate it
  C7.text：Using the maximum of sample-average estimates as an estimate of the maximum true value produces a positive maximization bias
  C3.text：the max operation over a collection of noisy or uncertain estimates Q(s, a) systematically yields a value that is biased upward relative to the true underlying values
- R2 核心：As a result, the maximum of the noisy action-value estimates overestimates the maximum of the true action values.
  判定：pass；C3 directly states that the max of noisy/uncertain estimates 'systematically yields a value that is biased upward relative to the true underlying values' and 'the maximum of uncertain estimates is higher than what the true values would dictate', which directly supports the claim that the maximum of noisy estimates overestimates the maximum of true action values. C7 also supports this by saying using the max of sample-average estimates as an estimate of the max true value produces a positive bias.
  C3.text：the max operation over a collection of noisy or uncertain estimates Q(s, a) systematically yields a value that is biased upward relative to the true underlying values
  C3.text：the maximum of uncertain estimates is higher than what the true values would dictate
  C7.text：Using the maximum of sample-average estimates as an estimate of the maximum true value produces a positive maximization bias

## KGGen / rl-qa-ch06-2

任务：t_1002ee988dfe671262a11fea

In the bandit discussion of maximization bias, what problem arises when the same noisy samples are used both to select the maximizing action and to estimate its value?

旧：fail；核心：fail；完整：fail

- R1 核心：Using the same samples both to select the maximizing action and to estimate its value produces a positive maximization bias.
  判定：fail；R1 requires stating that using the same samples both to select the maximizing action and to estimate its value produces a positive maximization bias. C1 ('Q-learning is due to using same samples in maximization bias') is a malformed triple that mentions same samples and maximization bias but does not state that the result is a 'positive' bias, nor does it describe the dual use of samples for both selection and estimation. C3 ('maximization bias appears to have positive value due to action B') mentions 'positive value' of maximization bias but attributes it to 'action B' rather than to the mechanism of using the same samples for selection and estimation. Neither candidate, individually or combined, supports the full claim of R1.
  C1.text：Q-learning is due to using same samples in maximization bias
  C3.text：maximization bias appears to have positive value due to action B
- R2 核心：As a result, the maximum of the noisy action-value estimates overestimates the maximum of the true action values.
  判定：fail；R2 requires stating that the maximum of the noisy action-value estimates overestimates the maximum of the true action values. None of the candidate assertions address the relationship between the maximum of noisy estimates and the maximum of true action values, nor mention overestimation. No candidate supports this claim.

## 我们的方法（强化学习） / rl-qa-ch06-2

任务：t_f439edb25827712d871b5d6d

In the bandit discussion of maximization bias, what problem arises when the same noisy samples are used both to select the maximizing action and to estimate its value?

旧：fail；核心：fail；完整：fail

- R1 核心：Using the same samples both to select the maximizing action and to estimate its value produces a positive maximization bias.
  判定：fail；候选中没有任何一条讨论使用相同样本既选择最大化动作又估计其价值会产生正的最大化偏差。C1讨论的是Double Learning作为解决方案（用Q1选动作、Q2提供无偏估计），但未提及偏差问题本身。
- R2 核心：As a result, the maximum of the noisy action-value estimates overestimates the maximum of the true action values.
  判定：fail；候选中没有任何一条提及噪声动作价值估计的最大值高估真实动作价值最大值的内容。

## AutoSchemaKG / rl-qa-ch07-1

任务：t_f3a9d1ff54ed3524d246822f

According to Section 7.6, how does the per-step choice between sampling (as in Sarsa) and taking an expectation over actions (as in the tree-backup update) recover n-step Sarsa, the tree-backup algorithm, and Expected Sarsa?

旧：fail；核心：pass；完整：pass

- R1 核心：The unification idea is to decide on a step-by-step basis at each transition whether to take the action as a sample (as in Sarsa) or to take the expectation over all actions (as in the tree-backup update).
  判定：pass；C2 explicitly states the unification idea: 'An idea for unification is proposed that decides on a step-by-step basis whether to take the action as a sample or consider the expectation over all actions.' This matches the requirement's description of deciding at each transition between sampling (Sarsa) and expectation (tree-backup).
  C2.text：An idea for unification is proposed that decides on a step-by-step basis whether to take the action as a sample or consider the expectation over all actions.
- R2 核心：If one always chose to sample, the result recovers n-step Sarsa.
  判定：pass；C2 describes n-step Sarsa as having 'all sample transitions,' which directly corresponds to always choosing to sample in the unification framework. Combined with the unification idea stated in C2, always sampling recovers n-step Sarsa.
  C2.text：n-step Sarsa has all sample transitions
- R3 核心：If one never chose to sample, the result recovers the tree-backup algorithm.
  判定：pass；C2 describes the tree-backup algorithm as having 'all state-to-action transitions fully branched without sampling,' which directly corresponds to never choosing to sample. Combined with the unification idea, never sampling recovers the tree-backup algorithm.
  C2.text：the tree-backup algorithm has all state-to-action transitions fully branched without sampling
- R4 核心：If one chose to sample for all steps except the last one, the result recovers Expected Sarsa.
  判定：pass；C2 describes n-step Expected Sarsa as having 'all sample transitions except for the last state-to-action one which is fully branched with an expected value.' This directly matches the requirement that sampling for all steps except the last one recovers Expected Sarsa.
  C2.text：n-step Expected Sarsa has all sample transitions except for the last state-to-action one which is fully branched with an expected value

## GraphRAG / rl-qa-ch07-1

任务：t_b9633bf148e6ea6849062345

According to Section 7.6, how does the per-step choice between sampling (as in Sarsa) and taking an expectation over actions (as in the tree-backup update) recover n-step Sarsa, the tree-backup algorithm, and Expected Sarsa?

旧：fail；核心：fail；完整：fail

- R1 核心：The unification idea is to decide on a step-by-step basis at each transition whether to take the action as a sample (as in Sarsa) or to take the expectation over all actions (as in the tree-backup update).
  判定：uncertain；C7 captures the general idea of unifying sampling (Sarsa) and expectation (tree-backup), and C1/C3 confirm the unification role of n-step Q(σ). However, no candidate explicitly states the key detail that the choice is made on a 'step-by-step basis at each transition' (i.e., independently at each step). The per-step / per-transition mechanism is missing from the candidates.
  C7.text：N-step Q(sigma) unifies algorithms that take expectations over actions (tree-backup) with those that sample actions (Sarsa)
  C1.text：Section 7.6 introduces n-step Q(sigma) as a unifying algorithm that brings together n-step Sarsa, Tree backup, and Expected Sarsa
- R2 核心：If one always chose to sample, the result recovers n-step Sarsa.
  判定：pass；C6 directly states that full sampling (sigma=1) yields Sarsa, supporting the claim that always choosing to sample recovers n-step Sarsa.
  C6.text：N-step Q(sigma) interpolates between full sampling (sigma=1, yielding Sarsa) and pure expectation with no sampling (sigma=0, yielding tree-backup)
- R3 核心：If one never chose to sample, the result recovers the tree-backup algorithm.
  判定：pass；C6 directly states that pure expectation with no sampling (sigma=0) yields tree-backup, supporting the claim that never choosing to sample recovers the tree-backup algorithm.
  C6.text：N-step Q(sigma) interpolates between full sampling (sigma=1, yielding Sarsa) and pure expectation with no sampling (sigma=0, yielding tree-backup)
- R4 核心：If one chose to sample for all steps except the last one, the result recovers Expected Sarsa.
  判定：fail；No candidate supports the specific claim that sampling for all steps except the last one recovers Expected Sarsa. C2 and C4 distinguish Expected Sarsa from tree-backup, but none describe the specific mechanism of 'sample for all steps except the last one' to obtain Expected Sarsa.
  C2.text：N-step Expected Sarsa was distinguished from n-step Tree Backup in Chapter 7
  C4.text：N-step Expected Sarsa uses importance sampling, unlike n-step Tree Backup

## KGGen / rl-qa-ch07-1

任务：t_ae376e756a0148a4c834a4bf

According to Section 7.6, how does the per-step choice between sampling (as in Sarsa) and taking an expectation over actions (as in the tree-backup update) recover n-step Sarsa, the tree-backup algorithm, and Expected Sarsa?

旧：fail；核心：fail；完整：fail

- R1 核心：The unification idea is to decide on a step-by-step basis at each transition whether to take the action as a sample (as in Sarsa) or to take the expectation over all actions (as in the tree-backup update).
  判定：fail；Candidates C6 ('n-step Q(σ) slides between tree-backup algorithm') and C9 ('n-step Q(σ) slides linearly between tree-backup algorithm') only vaguely mention that n-step Q(σ) slides between algorithms, but none describe the core unification mechanism: deciding on a step-by-step basis at each transition whether to sample the action (Sarsa-style) or take an expectation over all actions (tree-backup style). The specific per-step decision concept is absent.
  C6.text：n-step Q(σ) slides between tree-backup algorithm
  C9.text：n-step Q(σ) slides linearly between tree-backup algorithm
- R2 核心：If one always chose to sample, the result recovers n-step Sarsa.
  判定：fail；No candidate states that always choosing to sample recovers n-step Sarsa. C6 and C9 mention sliding between tree-backup and something else, but do not identify n-step Sarsa as the endpoint achieved by always sampling.
- R3 核心：If one never chose to sample, the result recovers the tree-backup algorithm.
  判定：fail；C6 and C9 identify the tree-backup algorithm as one endpoint of the n-step Q(σ) spectrum, but neither candidate states the specific condition ('never chose to sample') that yields the tree-backup algorithm. The explicit condition is missing.
  C6.text：n-step Q(σ) slides between tree-backup algorithm
  C9.text：n-step Q(σ) slides linearly between tree-backup algorithm
- R4 核心：If one chose to sample for all steps except the last one, the result recovers Expected Sarsa.
  判定：fail；C10 ('n-step Expected Sarsa is distinguished from n-step Tree Backup') and C4 ('Q-learning and Expected Sarsa is multi-step extension of n-step tree-backup algorithm') mention Expected Sarsa in relation to tree-backup, but neither describes the specific sampling pattern (sampling for all steps except the last one) that recovers Expected Sarsa. The required condition is absent.
  C10.text：n-step Expected Sarsa is distinguished from n-step Tree Backup
  C4.text：Q-learning and Expected Sarsa is multi-step extension of n-step tree-backup algorithm

## 我们的方法（强化学习） / rl-qa-ch07-1

任务：t_dea6c942b64db3dea9edb85a

According to Section 7.6, how does the per-step choice between sampling (as in Sarsa) and taking an expectation over actions (as in the tree-backup update) recover n-step Sarsa, the tree-backup algorithm, and Expected Sarsa?

旧：fail；核心：fail；完整：fail

- R1 核心：The unification idea is to decide on a step-by-step basis at each transition whether to take the action as a sample (as in Sarsa) or to take the expectation over all actions (as in the tree-backup update).
  判定：fail；No candidate describes the step-by-step (per-transition) decision mechanism of choosing between sampling and taking expectations, which is the core unification idea in Section 7.6 (Q(σ)). C4 only mentions that n-step Q(σ) uses the n-step Sarsa update rule but does not describe the per-step σ choice.
- R2 核心：If one always chose to sample, the result recovers n-step Sarsa.
  判定：fail；No candidate states that always choosing to sample recovers n-step Sarsa. C4 mentions Q(σ) uses n-step Sarsa's update rule but does not describe the 'always sample' case yielding n-step Sarsa.
- R3 核心：If one never chose to sample, the result recovers the tree-backup algorithm.
  判定：fail；No candidate states that never sampling recovers the tree-backup algorithm. C3, C7, C8, C9 describe properties of the tree-backup algorithm but none link it to the 'never choose to sample' condition in Q(σ).
- R4 核心：If one chose to sample for all steps except the last one, the result recovers Expected Sarsa.
  判定：fail；No candidate states that sampling for all steps except the last recovers Expected Sarsa. C2 and C6 discuss Expected Sarsa but do not describe the 'sample all but last step' condition in Q(σ).

## AutoSchemaKG / rl-qa-ch07-2

任务：t_e53b456d17b33d9fdd4c97c6

In the off-policy n-step state-value return with control variates (equation 7.13), what happens when the importance sampling ratio ρ_t is zero, and why does the control variate not change the expected update?

旧：pass；核心：fail；完整：fail

- R1 核心：When ρ_t = 0, the target in equation 7.13 reduces to V_{h-1}(S_t), which equals the current estimate, so applying the update causes no change.
  判定：fail；No candidate discusses what happens when ρ_t = 0, the target reducing to V_{h-1}(S_t), or that this equals the current estimate causing no change. C4 only states generically that the control variate does not change the expected update.
- R2 核心：An importance sampling ratio of zero means the sample should be ignored, so leaving the estimate unchanged is the appropriate behavior.
  判定：fail；No candidate states that an importance sampling ratio of zero means the sample should be ignored or that leaving the estimate unchanged is the appropriate behavior.
- R3 完整答案补充：If the return were simply weighted by ρ_t instead, a ratio of zero would make the n-step return zero and shrink the estimate, which can cause high variance; the control variate formulation avoids this.
  判定：fail；No candidate discusses the consequence of simply weighting the return by ρ_t (making it zero, shrinking the estimate, causing high variance) or that the control variate formulation avoids this.
- R4 核心：The control variate does not change the expected update because the importance sampling ratio ρ_t has expected value one and is uncorrelated with the estimate, so the expected value of the control variate term (1 − ρ_t)V_{h-1}(S_t) is zero.
  判定：pass；C1 directly states the control variate does not change the expected update because the importance sampling ratio has expected value one and is uncorrelated with the estimate. C3 states the expected value of the control variate is zero because the importance sampling ratio is uncorrelated with the estimate. Together these cover the full reasoning in R4.
  C1.text：The control variate does not change the expected update. because The importance sampling ratio has expected value one and is uncorrelated with the estimate.
  C3.text：The expected value of the control variate is zero. because The importance sampling ratio is uncorrelated with the estimate.

## GraphRAG / rl-qa-ch07-2

任务：t_2c1db8ea1bcabfe5916bcc03

In the off-policy n-step state-value return with control variates (equation 7.13), what happens when the importance sampling ratio ρ_t is zero, and why does the control variate not change the expected update?

旧：fail；核心：fail；完整：fail

- R1 核心：When ρ_t = 0, the target in equation 7.13 reduces to V_{h-1}(S_t), which equals the current estimate, so applying the update causes no change.
  判定：fail；No candidate explicitly states that when ρ_t = 0 the target in equation 7.13 reduces to V_{h-1}(S_t), which equals the current estimate, causing no change. C3 mentions the control variate addresses the case of zero ratios for variance reduction, but does not describe the specific mechanism of the target collapsing to the current value estimate.
  C3.text：The control variate modifies the off-policy n-step return to reduce variance when importance sampling ratios are zero
- R2 核心：An importance sampling ratio of zero means the sample should be ignored, so leaving the estimate unchanged is the appropriate behavior.
  判定：fail；No candidate states that an importance sampling ratio of zero means the sample should be ignored or that leaving the estimate unchanged is the appropriate behavior. C3 only vaguely refers to variance reduction when ratios are zero, which is related but does not express the behavioral consequence of ignoring the sample or leaving the estimate unchanged.
  C3.text：The control variate modifies the off-policy n-step return to reduce variance when importance sampling ratios are zero
- R3 完整答案补充：If the return were simply weighted by ρ_t instead, a ratio of zero would make the n-step return zero and shrink the estimate, which can cause high variance; the control variate formulation avoids this.
  判定：fail；No candidate explains the contrast between the simple ρ_t-weighted return (which would go to zero and shrink the estimate, causing high variance) and the control variate formulation that avoids this. C3 mentions variance reduction when ratios are zero but does not describe the specific mechanism involving the n-step return shrinking to zero.
  C3.text：The control variate modifies the off-policy n-step return to reduce variance when importance sampling ratios are zero
- R4 核心：The control variate does not change the expected update because the importance sampling ratio ρ_t has expected value one and is uncorrelated with the estimate, so the expected value of the control variate term (1 − ρ_t)V_{h-1}(S_t) is zero.
  判定：pass；C1 directly states that the control variate does not change the expected update because the importance sampling ratio has expected value one, which is the core reason given in the requirement. While the uncorrelated detail and the explicit form of the control variate term are not mentioned, the essential claim linking the expected-value-one property to the unchanged expected update is supported.
  C1.text：The control variate does not change the expected update because the importance sampling ratio has expected value one

## KGGen / rl-qa-ch07-2

任务：t_a709d84ee970260e549675f1

In the off-policy n-step state-value return with control variates (equation 7.13), what happens when the importance sampling ratio ρ_t is zero, and why does the control variate not change the expected update?

旧：uncertain；核心：fail；完整：fail

- R1 核心：When ρ_t = 0, the target in equation 7.13 reduces to V_{h-1}(S_t), which equals the current estimate, so applying the update causes no change.
  判定：fail；No candidate assertion describes the specific behavior of equation 7.13 when ρ_t = 0, i.e., that the target reduces to V_{h-1}(S_t) and the update causes no change. C7 only vaguely identifies equation 7.13 as 'the second additional term in control variate' without explaining the ρ_t = 0 case.
  C7.text：Equation 7.13 is the second additional term in control variate
- R2 核心：An importance sampling ratio of zero means the sample should be ignored, so leaving the estimate unchanged is the appropriate behavior.
  判定：fail；No candidate assertion states that an importance sampling ratio of zero means the sample should be ignored or that leaving the estimate unchanged is the appropriate behavior.
- R3 完整答案补充：If the return were simply weighted by ρ_t instead, a ratio of zero would make the n-step return zero and shrink the estimate, which can cause high variance; the control variate formulation avoids this.
  判定：fail；No candidate assertion discusses the alternative of simply weighting the return by ρ_t, the resulting high variance from shrinkage toward zero, or how the control variate formulation avoids this.
- R4 核心：The control variate does not change the expected update because the importance sampling ratio ρ_t has expected value one and is uncorrelated with the estimate, so the expected value of the control variate term (1 − ρ_t)V_{h-1}(S_t) is zero.
  判定：uncertain；C4 references that the control variate does not change the expected value (but only as an exercise prompt, not as an explanation), and C8 references that equation 5.13 states the expected value of the importance sampling ratio ρ. Together these touch on the ingredients (E[ρ]=1 and the fact that the expected update is unchanged) but neither candidate provides the full reasoning—that ρ_t is uncorrelated with the estimate and that E[(1−ρ_t)V_{h-1}(S_t)] = 0—so support is partial and ambiguous.
  C4.text：Gt:h asks to prove that control variate does not change expected value of Exercise 7.6
  C8.text：equation (5.13) states that expected value of importance sampling ratio ρ

## 我们的方法（强化学习） / rl-qa-ch07-2

任务：t_c877b84db007bfad86656cb8

In the off-policy n-step state-value return with control variates (equation 7.13), what happens when the importance sampling ratio ρ_t is zero, and why does the control variate not change the expected update?

旧：fail；核心：fail；完整：fail

- R1 核心：When ρ_t = 0, the target in equation 7.13 reduces to V_{h-1}(S_t), which equals the current estimate, so applying the update causes no change.
  判定：fail；No candidate addresses the specific mathematical consequence of ρ_t = 0 in equation 7.13—namely that the target reduces to V_{h-1}(S_t) and the update causes no change. C3 only mentions the control variate is an additional term; none of the candidates contain the reduction-to-current-estimate claim.
- R2 核心：An importance sampling ratio of zero means the sample should be ignored, so leaving the estimate unchanged is the appropriate behavior.
  判定：fail；No candidate states that an importance sampling ratio of zero means the sample should be ignored or that leaving the estimate unchanged is the appropriate behavior. C1 discusses expected-value properties, not the zero-case interpretation.
- R3 完整答案补充：If the return were simply weighted by ρ_t instead, a ratio of zero would make the n-step return zero and shrink the estimate, which can cause high variance; the control variate formulation avoids this.
  判定：fail；No candidate discusses what would happen with simple ρ_t weighting (without control variates), nor the resulting high-variance or estimate-shrinkage issues. This comparison is absent from the candidate set.
- R4 核心：The control variate does not change the expected update because the importance sampling ratio ρ_t has expected value one and is uncorrelated with the estimate, so the expected value of the control variate term (1 − ρ_t)V_{h-1}(S_t) is zero.
  判定：pass；C1 directly states that the control variate does not change the expected update because the importance sampling ratio has expected value one and is uncorrelated with the estimate, so the expected value of the control variate is zero. This fully covers the required reasoning.
  C1.text：The control variate does not change the expected update of the off-policy n-step return (state-value form), because the importance sampling ratio has expected value one and is uncorrelated with the estimate, so the expected value of the control variate is zero.

## AutoSchemaKG / rl-qa-ch08-1

任务：t_57feae2386627adc0b6aef97

According to the textbook's discussion of decision-time planning, how much computation time is typically permitted per move in chess playing programs, and how many moves ahead may strong programs plan within this time?

旧：fail；核心：fail；完整：fail

- R1 核心：In chess playing programs using decision-time planning, one may be permitted seconds or minutes of computation for each move.
  判定：fail；C1 confirms chess playing programs use decision-time planning, but no candidate provides the specific information that one may be permitted 'seconds or minutes' of computation for each move. The quantitative time allowance is missing.
  C1.text：chess playing programs use decision-time planning
- R2 核心：Within this time, strong programs may plan dozens of moves ahead.
  判定：fail；No candidate mentions that strong programs may plan 'dozens of moves ahead.' C4 discusses N-step methods looking ahead, but this is not specifically about chess strong programs planning dozens of moves. The specific claim about dozens of moves is missing from all candidates.

## GraphRAG / rl-qa-ch08-1

任务：t_81ca3987b60c085f17f55ba9

According to the textbook's discussion of decision-time planning, how much computation time is typically permitted per move in chess playing programs, and how many moves ahead may strong programs plan within this time?

旧：pass；核心：pass；完整：pass

- R1 核心：In chess playing programs using decision-time planning, one may be permitted seconds or minutes of computation for each move.
  判定：pass；C2 and C4 both explicitly state that chess playing programs are permitted seconds or minutes of computation for each move, and C4 connects this specifically to the decision-time planning paradigm.
  C2.text：Chess playing programs are permitted seconds or minutes of computation for each move
  C4.text：the program is permitted only a limited budget of computation—typically on the order of seconds or minutes per move
- R2 核心：Within this time, strong programs may plan dozens of moves ahead.
  判定：pass；C1 directly states that strong chess programs may plan dozens of moves ahead within the allotted time, fully supporting this requirement.
  C1.text：Strong chess programs may plan dozens of moves ahead within the allotted time

## KGGen / rl-qa-ch08-1

任务：t_e7bf29a0e461923c2ccab8e9

According to the textbook's discussion of decision-time planning, how much computation time is typically permitted per move in chess playing programs, and how many moves ahead may strong programs plan within this time?

旧：fail；核心：fail；完整：fail

- R1 核心：In chess playing programs using decision-time planning, one may be permitted seconds or minutes of computation for each move.
  判定：fail；No candidate mentions computation time (seconds or minutes) per move. C1 and C3 relate decision-time planning and computation to chess playing programs but provide no time-frame information.
- R2 核心：Within this time, strong programs may plan dozens of moves ahead.
  判定：fail；No candidate mentions planning dozens of moves ahead. None of the candidates discuss lookahead depth or the number of moves strong programs can plan.

## 我们的方法（强化学习） / rl-qa-ch08-1

任务：t_2b719429c87c60c17908effa

According to the textbook's discussion of decision-time planning, how much computation time is typically permitted per move in chess playing programs, and how many moves ahead may strong programs plan within this time?

旧：fail；核心：fail；完整：fail

- R1 核心：In chess playing programs using decision-time planning, one may be permitted seconds or minutes of computation for each move.
  判定：fail；No candidate mentions chess playing programs being permitted 'seconds or minutes' of computation per move. Candidates C1 and C2 discuss simulation time per move but in the context of AlphaGo's policy networks being too slow, not chess. C7 and C9 mention checkers, not chess. No candidate provides the required fact about chess computation time.
- R2 核心：Within this time, strong programs may plan dozens of moves ahead.
  判定：fail；No candidate mentions strong programs planning 'dozens of moves ahead' in chess. Candidates discuss AlphaGo, checkers, Go, and reinforcement learning, but none address planning depth of dozens of moves in chess playing programs.

## AutoSchemaKG / rl-qa-ch09-1

任务：t_a556e989961efb36d9f1b35f

What is the name of the identity (9.22) used to maintain the inverse matrix A_t^{-1} in LSTD, and what order of per-step computation and memory does the book attribute to it?

旧：pass；核心：fail；完整：fail

- R1 核心：The identity (9.22) is known as the Sherman-Morrison formula.
  判定：pass；C1 explicitly states that the inverse matrix is stored and maintained with the Sherman-Morrison formula, which is the name of identity (9.22) in the LSTD context.
  C1.subject：The inverse matrix is stored and maintained with the Sherman-Morrison formula.
- R2 核心：Although the formula looks complicated, it involves only vector-matrix and vector-vector multiplications.
  判定：fail；No candidate mentions that the formula looks complicated or that it involves only vector-matrix and vector-vector multiplications. None of the candidates address the internal structure of the formula.
- R3 核心：The per-step computation required to maintain the inverse matrix A_t^{-1} using (9.22) is O(d^2).
  判定：pass；C1 states that maintaining and using the stored inverse matrix (via the Sherman-Morrison formula) achieves O(d²) per-step computation, which matches the requirement.
  C1.object：The stored inverse matrix is used in the value computation, achieving O(d²) memory and per-step computation.
- R4 核心：The memory required to store and maintain A_t^{-1} is O(d^2), and it can then be used in (9.21) with the same O(d^2) memory and per-step computation.
  判定：pass；C1 indicates the stored inverse matrix (maintained via Sherman-Morrison) is used in the value computation with O(d²) memory and per-step computation. C2 confirms that the final computation (9.21) uses the inverse of A_t. Together these support that the O(d²) memory and per-step computation apply both to maintaining A_t^{-1} and to using it in (9.21).
  C1.object：The stored inverse matrix is used in the value computation, achieving O(d²) memory and per-step computation.
  C2.subject：The final computation (9.21) uses the inverse of A_t

## GraphRAG / rl-qa-ch09-1

任务：t_083e5798a4f296255bb7e6e7

What is the name of the identity (9.22) used to maintain the inverse matrix A_t^{-1} in LSTD, and what order of per-step computation and memory does the book attribute to it?

旧：pass；核心：fail；完整：fail

- R1 核心：The identity (9.22) is known as the Sherman-Morrison formula.
  判定：pass；C2 explicitly identifies the Sherman-Morrison formula as (9.22) used in LSTD to update the inverse matrix A_t^(-1).
  C2.text：LSTD uses the Sherman-Morrison formula (9.22) to efficiently update the inverse matrix A_t^(-1) with O(d^2) computation
- R2 核心：Although the formula looks complicated, it involves only vector-matrix and vector-vector multiplications.
  判定：fail；No candidate asserts that the formula involves only vector-matrix and vector-vector multiplications. C2 only mentions O(d^2) computation but does not describe the nature of the operations.
- R3 核心：The per-step computation required to maintain the inverse matrix A_t^{-1} using (9.22) is O(d^2).
  判定：pass；C2 directly states that the Sherman-Morrison formula (9.22) updates the inverse matrix A_t^(-1) with O(d^2) computation per step.
  C2.text：LSTD uses the Sherman-Morrison formula (9.22) to efficiently update the inverse matrix A_t^(-1) with O(d^2) computation
- R4 核心：The memory required to store and maintain A_t^{-1} is O(d^2), and it can then be used in (9.21) with the same O(d^2) memory and per-step computation.
  判定：fail；No candidate states the O(d^2) memory required for A_t^(-1) nor mentions equation (9.21) or that it uses the same O(d^2) memory and per-step computation. C7 mentions O(d^2) memory but for the A_t matrix, not A_t^(-1), and does not reference (9.21).
  C7.text：LSTD requires O(d^2) memory to hold the A_t matrix

## KGGen / rl-qa-ch09-1

任务：t_4d72b4e6e9c7f1932f7b33c8

What is the name of the identity (9.22) used to maintain the inverse matrix A_t^{-1} in LSTD, and what order of per-step computation and memory does the book attribute to it?

旧：pass；核心：fail；完整：fail

- R1 核心：The identity (9.22) is known as the Sherman-Morrison formula.
  判定：pass；C2 directly identifies the Sherman-Morrison formula as identity (9.22).
  C2.text：Sherman-Morrison formula is the identity (9.22) O(d²) computation
- R2 核心：Although the formula looks complicated, it involves only vector-matrix and vector-vector multiplications.
  判定：fail；No candidate mentions that the formula involves only vector-matrix and vector-vector multiplications. None of the candidates discuss the nature of the multiplications involved in (9.22).
- R3 核心：The per-step computation required to maintain the inverse matrix A_t^{-1} using (9.22) is O(d^2).
  判定：pass；C2 explicitly states O(d²) computation in the context of the Sherman-Morrison formula as identity (9.22), supporting the O(d²) per-step computation claim.
  C2.text：Sherman-Morrison formula is the identity (9.22) O(d²) computation
- R4 核心：The memory required to store and maintain A_t^{-1} is O(d^2), and it can then be used in (9.21) with the same O(d^2) memory and per-step computation.
  判定：fail；No candidate mentions O(d²) memory for storing/maintaining A_t^{-1}, nor mentions that (9.21) can be used with the same O(d²) memory and per-step computation. C5 only states that LSTD stores the inverse matrix without specifying O(d²) memory.
  C5.text：LSTD (Least Squares Temporal Difference) stores inverse matrix

## 我们的方法（强化学习） / rl-qa-ch09-1

任务：t_d9917d1d7a1c8d26302ccde7

What is the name of the identity (9.22) used to maintain the inverse matrix A_t^{-1} in LSTD, and what order of per-step computation and memory does the book attribute to it?

旧：fail；核心：fail；完整：fail

- R1 核心：The identity (9.22) is known as the Sherman-Morrison formula.
  判定：fail；No candidate mentions the Sherman-Morrison formula or identity (9.22).
- R2 核心：Although the formula looks complicated, it involves only vector-matrix and vector-vector multiplications.
  判定：fail；No candidate discusses vector-matrix and vector-vector multiplications in the context of identity (9.22).
- R3 核心：The per-step computation required to maintain the inverse matrix A_t^{-1} using (9.22) is O(d^2).
  判定：fail；No candidate attributes O(d^2) per-step computation to maintaining A_t^{-1} using (9.22). C1 only mentions O(d) for TD(0), not O(d^2) for the Sherman-Morrison update.
- R4 核心：The memory required to store and maintain A_t^{-1} is O(d^2), and it can then be used in (9.21) with the same O(d^2) memory and per-step computation.
  判定：fail；No candidate mentions O(d^2) memory for storing/maintaining A_t^{-1} or its use in equation (9.21) with the same O(d^2) cost.

## AutoSchemaKG / rl-qa-ch10-1

任务：t_5b42c1ee1b4f407d89f29b2b

What limitation does the chapter identify for local policy improvement guarantees in action-value methods once function approximation is introduced?

旧：pass；核心：uncertain；完整：fail

- R1 核心：Once function approximation is introduced, local policy improvement is no longer guaranteed for action-value methods.
  判定：pass；Combined support from multiple candidates establishes that with function approximation, the local policy improvement guarantee is lost for action-value methods. C1 establishes the loss of guarantee when function approximation is introduced; C2 specifically identifies action-value methods as having no local improvement guarantee; C7 confirms the policy improvement theorem is lacking for function approximation.
  C1.subject：Once function approximation is introduced, improvement can no longer be guaranteed for any setting.
  C2.subject：For methods that learn action values, there is currently no local improvement guarantee.
  C7.text：policy improvement theorem lacks for function approximation
- R2 核心：The loss of a local policy improvement guarantee applies across all settings, including the total-episodic and average-reward settings.
  判定：uncertain；C1 states improvement 'can no longer be guaranteed for any setting,' which is consistent with applying across all settings. However, the candidate does not specifically identify the total-episodic and average-reward settings, which the requirement asks the chapter to identify. The general claim is supported but the specific identification of these two settings is missing from the candidates.
  C1.subject：Once function approximation is introduced, improvement can no longer be guaranteed for any setting.
- R3 完整答案补充：ε-greedification may sometimes result in an inferior policy, rather than guaranteeing improvement.
  判定：pass；C2 directly states that 'Epsilon-greedification may sometimes result in an inferior policy,' which supports the requirement that ε-greedification may sometimes produce an inferior policy rather than guaranteeing improvement.
  C2.object：Epsilon-greedification may sometimes result in an inferior policy.
- R4 完整答案补充：Policies may chatter among good policies rather than converge.
  判定：fail；No candidate addresses chattering among good policies or failure to converge. The claim is entirely absent from the candidate assertions.

## GraphRAG / rl-qa-ch10-1

任务：t_4660b92cde74b71e61fd6fb7

What limitation does the chapter identify for local policy improvement guarantees in action-value methods once function approximation is introduced?

旧：pass；核心：fail；完整：fail

- R1 核心：Once function approximation is introduced, local policy improvement is no longer guaranteed for action-value methods.
  判定：pass；C1 directly states the local improvement guarantee is lacking for action-value learning methods with function approximation, and C3 reinforces this as an open theoretical question. Together they fully support that local policy improvement is no longer guaranteed for action-value methods once function approximation is introduced.
  C1.text：The local improvement guarantee is lacking for action-value learning methods with function approximation
  C3.text：Open theoretical questions include the lack of a local improvement guarantee for action-value learning methods
- R2 核心：The loss of a local policy improvement guarantee applies across all settings, including the total-episodic and average-reward settings.
  判定：fail；None of the candidate assertions mention the total-episodic setting or the average-reward setting. The generality across all settings is not supported by any candidate.
- R3 完整答案补充：ε-greedification may sometimes result in an inferior policy, rather than guaranteeing improvement.
  判定：fail；C6 mentions epsilon-greedy as an example of local policy improvement, but no candidate states that epsilon-greedification may result in an inferior policy. The required claim about potential inferiority is not supported.
  C6.text：An example of local policy improvement with respect to the current value function is being epsilon-greedy
- R4 完整答案补充：Policies may chatter among good policies rather than converge.
  判定：fail；No candidate assertion mentions chattering among policies or lack of convergence in this sense. The claim is unsupported by the candidates.

## KGGen / rl-qa-ch10-1

任务：t_b637ae7570c0f538db00bb15

What limitation does the chapter identify for local policy improvement guarantees in action-value methods once function approximation is introduced?

旧：fail；核心：fail；完整：fail

- R1 核心：Once function approximation is introduced, local policy improvement is no longer guaranteed for action-value methods.
  判定：fail；No candidate states that local policy improvement is no longer guaranteed for action-value methods once function approximation is introduced. C1 only notes that linear function approximation is introduced in Chapter 11; C9 only states action-value prediction methods are coupled with policy improvement. The specific claim about loss of a local improvement guarantee is absent.
- R2 核心：The loss of a local policy improvement guarantee applies across all settings, including the total-episodic and average-reward settings.
  判定：fail；No candidate mentions the scope of settings (total-episodic, average-reward) over which the loss of the local policy improvement guarantee applies. The required content is entirely absent from the candidates.
- R3 完整答案补充：ε-greedification may sometimes result in an inferior policy, rather than guaranteeing improvement.
  判定：fail；No candidate mentions ε-greedification or that it may produce an inferior policy. The required content is entirely absent.
- R4 完整答案补充：Policies may chatter among good policies rather than converge.
  判定：fail；No candidate mentions chattering among good policies or lack of convergence. The required content is entirely absent.

## 我们的方法（强化学习） / rl-qa-ch10-1

任务：t_608632bd9391870ea17a4afd

What limitation does the chapter identify for local policy improvement guarantees in action-value methods once function approximation is introduced?

旧：fail；核心：pass；完整：fail

- R1 核心：Once function approximation is introduced, local policy improvement is no longer guaranteed for action-value methods.
  判定：pass；C8 directly states that once function approximation is introduced, the policy improvement theorem no longer holds and policy improvement can no longer be guaranteed.
  C8.object：策略改进定理（强化学习）
  C8.text：Once 函数近似（强化学习） is introduced, the 策略改进定理（强化学习） no longer holds and we can no longer guarantee policy improvement in any setting (discounted, total-episodic, or average-reward).
- R2 核心：The loss of a local policy improvement guarantee applies across all settings, including the total-episodic and average-reward settings.
  判定：pass；C8 explicitly lists all settings including total-episodic and average-reward as settings where policy improvement can no longer be guaranteed once function approximation is introduced.
  C8.text：we can no longer guarantee policy improvement in any setting (discounted, total-episodic, or average-reward).
- R3 完整答案补充：ε-greedification may sometimes result in an inferior policy, rather than guaranteeing improvement.
  判定：fail；No candidate assertion mentions that ε-greedification may result in an inferior policy. C9 only describes ε-greedy as a soft approximation of greedy selection used to perform policy improvement, without addressing the possibility of an inferior resulting policy.
- R4 完整答案补充：Policies may chatter among good policies rather than converge.
  判定：fail；No candidate assertion mentions policies chattering among good policies rather than converging. None of the candidates address this behavior.

## AutoSchemaKG / rl-qa-ch11-1

任务：t_0fad674c075000decbbd1cb0

What does the A-presplit example illustrate about minimizing the Bellman Error (BE) with the residual-gradient algorithm?

旧：pass；核心：pass；完整：pass

- R1 核心：In the A-presplit example (a variation on the A-split example with genuine function approximation), the residual-gradient algorithm finds the same poor solution as its naive version.
  判定：pass；Candidates C1 and C7 together support that the residual-gradient algorithm finds the same poor solution as its naive version in the A-presplit example. C1 explicitly states the A-presplit example shows the residual-gradient algorithm finding the same poor solution as its naive version, and C7 confirms the non-naive (residual-gradient) algorithm converges to the same values as the naive version. The detail about A-presplit being 'a variation on the A-split example with genuine function approximation' is not explicitly stated but the core claim of R1 is supported.
  C1.text：The A-presplit example shows the residual-gradient algorithm finding the same poor solution as its naive version because minimizing the BE may not be a desirable goal
  C7.text：The system in the A-presplit example is deterministic as a result the non-naive residual-gradient algorithm will also converge to the same values as the naive version
- R2 核心：This illustrates that minimizing the Bellman Error (BE) may not be a desirable goal, since minimizing BE leads to the wrong value functions.
  判定：pass；C1 directly states 'minimizing the BE may not be a desirable goal,' which matches the first part of R2. C3 states the naive residual-gradient algorithm 'converges to wrong values' in the A-presplit example, supporting that minimizing BE leads to wrong value functions. C8 reinforces that 'optimizing Bellman Error gives rise to failure mode in A-presplit example.' Together these support the illustration that minimizing BE may not be desirable since it leads to wrong value functions.
  C1.text：minimizing the BE may not be a desirable goal
  C3.text：naive residual-gradient algorithm converges to wrong values in A-presplit example
  C8.text：optimizing Bellman Error gives rise to failure mode in A-presplit example
- R3 完整答案补充：The problem shown by this example is a problem with the BE objective itself rather than with any particular algorithm for achieving it.
  判定：pass；C10 directly identifies the 'Bellman Error objective' as the problem, supporting the idea that the issue lies with the BE objective itself. C8 states that 'optimizing Bellman Error gives rise to failure mode,' indicating the problem is inherent to the BE objective. C4 further reinforces this by showing the failure mode arises from optimizing BE, not from a specific algorithmic deficiency. Together these support that the problem is with the BE objective rather than with any particular algorithm for achieving it.
  C4.text：The BE is optimized on the A-presplit example as a result it gives rise to the same failure mode as with the naive residual-gradient algorithm on the A-split example
  C8.text：optimizing Bellman Error gives rise to failure mode in A-presplit example
  C10.text：Bellman Error objective is problem of residual-gradient algorithm

## GraphRAG / rl-qa-ch11-1

任务：t_55a40c3e695c670e08034a50

What does the A-presplit example illustrate about minimizing the Bellman Error (BE) with the residual-gradient algorithm?

旧：pass；核心：pass；完整：pass

- R1 核心：In the A-presplit example (a variation on the A-split example with genuine function approximation), the residual-gradient algorithm finds the same poor solution as its naive version.
  判定：pass；C4 directly supports the core claim: 'the non-naive residual-gradient algorithm finds the same poor solution as its naive version' on the A-presplit example. The 'genuine function approximation' detail in R1 is not directly confirmed by candidates (C9 even describes it as a 'tabular case'), but the main algorithmic point is supported.
  C4.text：On the A-presplit example, the non-naive residual-gradient algorithm finds the same poor solution as its naive version, showing the BE objective may be undesirable
- R2 核心：This illustrates that minimizing the Bellman Error (BE) may not be a desirable goal, since minimizing BE leads to the wrong value functions.
  判定：pass；C2 directly states 'The A-presplit example shows that minimizing the BE may not be a desirable goal', and C4 reinforces this by showing the BE objective leads to undesirable solutions. C3 and C5 further support that minimizing BE leads to wrong values (residual-gradient doesn't converge to ideal values, but rather to 3/4 and 1/4 which minimize BE).
  C2.text：The A-presplit example shows that minimizing the BE may not be a desirable goal
  C4.text：showing the BE objective may be undesirable
  C3.text：On the A-presplit example, semi-gradient TD converges to the ideal values while the residual-gradient algorithm does not
- R3 完整答案补充：The problem shown by this example is a problem with the BE objective itself rather than with any particular algorithm for achieving it.
  判定：pass；C4 supports this requirement by showing that both the naive and non-naive (BE-minimizing) versions of the residual-gradient algorithm arrive at the same poor solution. This indicates the problem lies with the BE objective itself rather than with any particular algorithm's implementation, since different algorithmic approaches yield the same undesirable result.
  C4.text：On the A-presplit example, the non-naive residual-gradient algorithm finds the same poor solution as its naive version, showing the BE objective may be undesirable

## KGGen / rl-qa-ch11-1

任务：t_ab788a8ccf64e5e36575d78c

What does the A-presplit example illustrate about minimizing the Bellman Error (BE) with the residual-gradient algorithm?

旧：pass；核心：uncertain；完整：uncertain

- R1 核心：In the A-presplit example (a variation on the A-split example with genuine function approximation), the residual-gradient algorithm finds the same poor solution as its naive version.
  判定：uncertain；C1 states the A-presplit example has the 'same failure mode' as the naive residual-gradient algorithm, and C2 shows the naive algorithm converges to 3/4 and 1/4, but no candidate explicitly states that the (proper) residual-gradient algorithm converges to the same poor solution. The inference is plausible (both minimize BE, so the example's failure should affect both) but not directly stated.
  C1.text：A-presplit example has same failure mode as naive residual-gradient algorithm in BE objective
  C2.text：A-presplit example converges to 3/4 for B and 1/4 for C in naive residual-gradient algorithm
- R2 核心：This illustrates that minimizing the Bellman Error (BE) may not be a desirable goal, since minimizing BE leads to the wrong value functions.
  判定：pass；C6 directly states that the A-presplit example shows minimizing BE 'may not be a desirable goal.' C2 provides the specific poor convergence values (3/4 for B, 1/4 for C) and C5 frames BE as a 'counterexample' for the A-presplit example, together supporting that minimizing BE leads to wrong/undesirable value functions.
  C6.text：A-presplit example may not be a desirable goal to minimize BE objective
  C2.text：A-presplit example converges to 3/4 for B and 1/4 for C in naive residual-gradient algorithm
  C5.text：BEs (Bellman Errors) is a counterexample for A-presplit example
- R3 完整答案补充：The problem shown by this example is a problem with the BE objective itself rather than with any particular algorithm for achieving it.
  判定：pass；C1 locates the failure 'in BE objective' (attributing the problem to the objective, not the algorithm), and C6 frames the issue as the BE minimization 'goal' itself being undesirable. Together they support the claim that the problem is with the BE objective rather than with any particular algorithm.
  C1.text：A-presplit example has same failure mode as naive residual-gradient algorithm in BE objective
  C6.text：A-presplit example may not be a desirable goal to minimize BE objective

## 我们的方法（强化学习） / rl-qa-ch11-1

任务：t_684d823d8d949d9919cf322b

What does the A-presplit example illustrate about minimizing the Bellman Error (BE) with the residual-gradient algorithm?

旧：fail；核心：fail；完整：fail

- R1 核心：In the A-presplit example (a variation on the A-split example with genuine function approximation), the residual-gradient algorithm finds the same poor solution as its naive version.
  判定：fail；No candidate mentions the 'A-presplit' example or 'genuine function approximation'. C2 explicitly limits the residual-gradient algorithm's correct performance to tabular cases of the A-split example. C3, C4, C7, and C10 all concern the A-split example (tabular), not the A-presplit example. There is no candidate showing that in the A-presplit example the residual-gradient algorithm converges to the same poor solution as the naive version.
  C2.text：The Residual-gradient algorithm (reinforcement learning) obtains the correct values in all tabular cases, such as the Example 11.2: A-split example, because an exact solution to the Bellman equation is possible for tabular representations.
- R2 核心：This illustrates that minimizing the Bellman Error (BE) may not be a desirable goal, since minimizing BE leads to the wrong value functions.
  判定：fail；No candidate supports the claim that minimizing BE is undesirable because it leads to wrong value functions in the A-presplit example. C6 discusses BE learnability but with reference to Example 11.4 (a different example about two MRPs with the same data distribution), not the A-presplit example. C7 states the naive algorithm's wrong values in the A-split example minimize the TDE, not the BE. The specific illustration via A-presplit is absent.
  C6.text：The optimal parameter of the Bellman error (BE) lacks 可学习性（强化学习）, as demonstrated by Example 11.4 in which two Markov reward processes generate the same data distribution but have different BE-minimizing parameter vectors.
- R3 完整答案补充：The problem shown by this example is a problem with the BE objective itself rather than with any particular algorithm for achieving it.
  判定：fail；No candidate states that the problem in the A-presplit example lies with the BE objective itself rather than with any particular algorithm. The candidates discuss the naive residual-gradient algorithm (C3, C4, C7), the residual-gradient algorithm (C2, C9, C10), and BE learnability via a different example (C6), but none make the conceptual point that the BE objective is the problem rather than any algorithm.
  C6.text：The optimal parameter of the Bellman error (BE) lacks 可学习性（强化学习）, as demonstrated by Example 11.4 in which two Markov reward processes generate the same data distribution but have different BE-minimizing parameter vectors.

## AutoSchemaKG / rl-qa-ch12-1

任务：t_660f59579fe79224cf83d3c2

According to Chapter 12's conclusions, in what kind of application do eligibility trace methods typically not pay off computationally, and why?

旧：pass；核心：pass；完整：pass

- R1 核心：Eligibility trace methods typically do not pay off computationally in off-line applications where data can be generated cheaply, such as from an inexpensive simulation.
  判定：pass；C1 directly states that in off-line applications where data can be generated cheaply (e.g., from an inexpensive simulation), it often does not pay to use eligibility traces, matching the requirement.
  C1.subject：In off-line applications in which data can be generated cheaply, perhaps from an inexpensive simulation, then it often does not pay to use eligibility traces.
- R2 核心：The reason is that in these off-line settings the objective is to process as much data as possible as quickly as possible, rather than to extract more learning from a limited amount of data; thus the per-datum speedup provided by traces is generally not worth their extra computational cost, and one-step methods are favored.
  判定：pass；C1's object provides the core reason: the speedup per datum due to traces is typically not worth their computational cost, and one-step methods are favored. This matches the essential reasoning in R2, even though the candidate does not explicitly state the contrasting objective of 'processing as much data as possible vs. extracting more learning from limited data.'
  C1.object：In these cases the speedup per datum due to traces is typically not worth their computational cost, and one-step methods are favored.

## GraphRAG / rl-qa-ch12-1

任务：t_9326632faeef17ea560c4800

According to Chapter 12's conclusions, in what kind of application do eligibility trace methods typically not pay off computationally, and why?

旧：fail；核心：fail；完整：fail

- R1 核心：Eligibility trace methods typically do not pay off computationally in off-line applications where data can be generated cheaply, such as from an inexpensive simulation.
  判定：fail；No candidate mentions off-line applications, cheap data generation, or simulations. The candidates only discuss eligibility trace equations, exercises, and chapter references, with no information about the specific application domain where traces do not pay off.
- R2 核心：The reason is that in these off-line settings the objective is to process as much data as possible as quickly as possible, rather than to extract more learning from a limited amount of data; thus the per-datum speedup provided by traces is generally not worth their extra computational cost, and one-step methods are favored.
  判定：fail；No candidate discusses the trade-off between per-datum speedup and computational cost of eligibility traces, nor the preference for one-step methods in off-line settings. All candidates concern technical definitions and exercises related to eligibility traces, with no information about computational cost reasoning.

## KGGen / rl-qa-ch12-1

任务：t_401ada275e54ec5b7164cb0c

According to Chapter 12's conclusions, in what kind of application do eligibility trace methods typically not pay off computationally, and why?

旧：fail；核心：fail；完整：fail

- R1 核心：Eligibility trace methods typically do not pay off computationally in off-line applications where data can be generated cheaply, such as from an inexpensive simulation.
  判定：fail；No candidate assertion mentions off-line applications, cheap data generation, or inexpensive simulations. The candidates only discuss what eligibility traces are, where they are covered (Chapter 12), and related properties (fading, STDP, bootstrapping), but none address the specific context in which eligibility trace methods do not pay off computationally.
- R2 核心：The reason is that in these off-line settings the objective is to process as much data as possible as quickly as possible, rather than to extract more learning from a limited amount of data; thus the per-datum speedup provided by traces is generally not worth their extra computational cost, and one-step methods are favored.
  判定：fail；No candidate assertion discusses the reasoning about processing data quickly, per-datum speedup, extra computational cost of traces, or the preference for one-step methods in off-line settings. None of the candidates address why traces are or are not computationally worthwhile.

## 我们的方法（强化学习） / rl-qa-ch12-1

任务：t_d751cffe77740af3b4e8c310

According to Chapter 12's conclusions, in what kind of application do eligibility trace methods typically not pay off computationally, and why?

旧：fail；核心：fail；完整：fail

- R1 核心：Eligibility trace methods typically do not pay off computationally in off-line applications where data can be generated cheaply, such as from an inexpensive simulation.
  判定：pass；C1 explicitly states that in off-line applications where data can be generated cheaply, it often does not pay to use eligibility traces, directly supporting this requirement.
  C1.text：In off-line applications where data can be generated cheaply, one-step temporal-difference methods are favored over Eligibility traces and it often does not pay to use Eligibility traces.
- R2 核心：The reason is that in these off-line settings the objective is to process as much data as possible as quickly as possible, rather than to extract more learning from a limited amount of data; thus the per-datum speedup provided by traces is generally not worth their extra computational cost, and one-step methods are favored.
  判定：fail；C1 only states the conclusion that one-step TD methods are favored and eligibility traces do not pay off, but does not provide the specific reasoning about the objective being to process as much data as possible as quickly as possible, the contrast with extracting more learning from limited data, or the per-datum speedup versus extra computational cost trade-off. No other candidate contains this reasoning.

## AutoSchemaKG / rl-qa-ch13-1

任务：t_ce307f4a07ac282689d7ac22

According to the textbook, what kind of return does REINFORCE use, and when are its parameter updates performed?

旧：fail；核心：fail；完整：fail

- R1 核心：REINFORCE uses the complete return from time t, which includes all future rewards up until the end of the episode.
  判定：fail；No candidate discusses the complete return from time t or that REINFORCE uses all future rewards up to the end of the episode. C9 only mentions REINFORCE is a Monte Carlo method, which is tangential.
- R2 核心：REINFORCE is a Monte Carlo algorithm and is well defined only for the episodic case.
  判定：fail；C9 states 'REINFORCE is a Monte Carlo method for learning the policy parameter,' which directly supports the first part of R2. However, the second part—that REINFORCE is 'well defined only for the episodic case'—is not stated in any candidate. Since the episodic-case claim is necessary content that is missing, the requirement is not fully supported.
  C9.subject：REINFORCE is a Monte Carlo method for learning the policy parameter.
- R3 核心：All parameter updates are made in retrospect after the episode is completed (i.e., only at the end of the episode, not during it).
  判定：fail；C7 describes an 'offline algorithm' that makes no weight-vector changes during the episode and performs updates at the end using the semi-gradient rule with the λ-return as target. This is about a different algorithm (offline λ-return for value estimation), not REINFORCE (a policy gradient algorithm). No candidate addresses REINFORCE's parameter update timing specifically.
  C7.subject：The offline algorithm makes no changes to the weight vector during the episode.
  C7.object：At the end of the episode, a whole sequence of offline updates are made according to the semi-gradient rule using the λ-return as the target.

## GraphRAG / rl-qa-ch13-1

任务：t_e457ed9b1ea589260dbb46c1

According to the textbook, what kind of return does REINFORCE use, and when are its parameter updates performed?

旧：fail；核心：uncertain；完整：uncertain

- R1 核心：REINFORCE uses the complete return from time t, which includes all future rewards up until the end of the episode.
  判定：pass；C4 explicitly states that REINFORCE uses the actual Monte Carlo return Gt, described as 'the sum of discounted rewards from t to the end of the episode', which matches the requirement that REINFORCE uses the complete return from time t including all future rewards up until the end of the episode. C2 and C8 also support that REINFORCE uses the return Gt.
  C4.text：REINFORCE with baseline uses the actual Monte Carlo return Gt, the sum of discounted rewards from t to the end of the episode, as the target for updates
  C2.text：The Monte-Carlo REINFORCE update uses the return G_t to update the policy parameter θ_t
- R2 核心：REINFORCE is a Monte Carlo algorithm and is well defined only for the episodic case.
  判定：uncertain；C1 and C2 identify REINFORCE as a Monte-Carlo algorithm, supporting the first part of the requirement. However, no candidate explicitly states that REINFORCE is 'well defined only for the episodic case.' The episodic nature is implied by C4's mention of 'from t to the end of the episode', but the explicit restriction that it is well-defined only for the episodic case is not stated.
  C1.text：The Monte-Carlo REINFORCE update updates the policy parameter θ_t to θ_{t+1}
  C4.text：REINFORCE with baseline uses the actual Monte Carlo return Gt, the sum of discounted rewards from t to the end of the episode, as the target for updates
- R3 核心：All parameter updates are made in retrospect after the episode is completed (i.e., only at the end of the episode, not during it).
  判定：uncertain；No candidate explicitly states that all REINFORCE parameter updates are made after the episode is completed or only at the end of the episode. C6's mention of updates being applied 'upon receipt of return G_t' suggests updates occur when the return is available (which is at the end of an episode in Monte Carlo), but this is an inference rather than an explicit statement. The direct claim that updates happen only in retrospect after episode completion is not found in the candidates.
  C6.text：The Monte-Carlo REINFORCE update is applied to update the parameter θ_t of a Bernoulli-logistic unit upon receipt of return G_t

## KGGen / rl-qa-ch13-1

任务：t_d766ae67d8201abb7b4c6cd9

According to the textbook, what kind of return does REINFORCE use, and when are its parameter updates performed?

旧：fail；核心：fail；完整：fail

- R1 核心：REINFORCE uses the complete return from time t, which includes all future rewards up until the end of the episode.
  判定：fail；No candidate mentions that REINFORCE uses the 'complete return' from time t or that it includes all future rewards up to the end of the episode. C4 only mentions 'Monte-Carlo REINFORCE updates policy parameter θ' without specifying the return structure.
- R2 核心：REINFORCE is a Monte Carlo algorithm and is well defined only for the episodic case.
  判定：fail；C4 mentions 'Monte-Carlo REINFORCE' which partially supports REINFORCE being a Monte Carlo algorithm, but no candidate states that REINFORCE is 'well defined only for the episodic case.' The episodic requirement is unsupported.
  C4.text：Monte-Carlo REINFORCE updates policy parameter θ
- R3 核心：All parameter updates are made in retrospect after the episode is completed (i.e., only at the end of the episode, not during it).
  判定：fail；No candidate specifies that REINFORCE's parameter updates are made after the episode is completed (only at the end, not during). C4 only says REINFORCE updates policy parameter θ without any timing information. C2 and C7 reference 'off-line updates' but in the context of semi-gradient and λ-return, not REINFORCE.

## 我们的方法（强化学习） / rl-qa-ch13-1

任务：t_e075f76032bc3d644d998731

According to the textbook, what kind of return does REINFORCE use, and when are its parameter updates performed?

旧：fail；核心：fail；完整：fail

- R1 核心：REINFORCE uses the complete return from time t, which includes all future rewards up until the end of the episode.
  判定：fail；No candidate assertion mentions REINFORCE or the complete return from time t used by REINFORCE. None of the candidates discuss REINFORCE's return definition.
- R2 核心：REINFORCE is a Monte Carlo algorithm and is well defined only for the episodic case.
  判定：fail；No candidate assertion identifies REINFORCE as a Monte Carlo algorithm or states it is well defined only for the episodic case. C5 discusses the offline λ-return algorithm being episodic, but does not mention REINFORCE.
- R3 核心：All parameter updates are made in retrospect after the episode is completed (i.e., only at the end of the episode, not during it).
  判定：fail；No candidate assertion states that REINFORCE performs all parameter updates only at the end of the episode. C5 discusses the offline λ-return algorithm updating only at the end, but does not connect this to REINFORCE.

## AutoSchemaKG / rl-qa-ch14-1

任务：t_265152d1079f24208daecf1f

Why, according to the chapter, is higher-order conditioning difficult to demonstrate above the second order, and under what circumstances can it still be shown?

旧：fail；核心：fail；完整：fail

- R1 核心：Higher-order conditioning is difficult to demonstrate above the second order because a higher-order reinforcer loses its reinforcing value, since during higher-order conditioning trials it is not repeatedly followed by the original US.
  判定：pass；C1 states that extinction of conditioned reinforcement occurs in higher-order conditioning trials, which is the mechanism by which the higher-order reinforcer loses its value (since it is not being followed by the US), and as a result it becomes difficult to demonstrate higher-order conditioning. This supports the core reasoning that the reinforcer's loss of value explains the difficulty, though the candidate does not explicitly restrict the claim to 'above the second order.'
  C1.text：Extinction of conditioned reinforcement occurs in higher-order conditioning trials. as a result It becomes difficult to demonstrate higher-order conditioning.
- R2 核心：Under the right conditions, higher-order conditioning beyond the second order can be demonstrated by intermixing first-order trials with higher-order trials.
  判定：fail；No candidate mentions intermixing first-order trials with higher-order trials as a condition under which higher-order conditioning beyond the second order can be demonstrated. C2 only restates that extinction makes demonstration difficult; none of the candidates describe a procedure for overcoming this difficulty via trial intermixing.
- R3 核心：Higher-order conditioning beyond the second order can also be demonstrated by providing a general energizing stimulus.
  判定：fail；No candidate mentions a 'general energizing stimulus' as a means of demonstrating higher-order conditioning beyond the second order. None of the candidates address this condition at all.

## GraphRAG / rl-qa-ch14-1

任务：t_6c5e536c00b488eecd268e68

Why, according to the chapter, is higher-order conditioning difficult to demonstrate above the second order, and under what circumstances can it still be shown?

旧：pass；核心：pass；完整：pass

- R1 核心：Higher-order conditioning is difficult to demonstrate above the second order because a higher-order reinforcer loses its reinforcing value, since during higher-order conditioning trials it is not repeatedly followed by the original US.
  判定：pass；C5 directly states that higher-order conditioning is difficult because a higher-order reinforcer loses its reinforcing value without repeated pairing with the original US, matching the requirement's explanation. C7 also supports the mechanism by noting higher-order trials function as extinction trials because the US is absent.
  C5.text：Higher-order conditioning is difficult because a higher-order reinforcer loses its reinforcing value without repeated pairing with the original US
  C7.text：Higher-order conditioning trials function as extinction trials for the second-order CS because the US is absent
- R2 核心：Under the right conditions, higher-order conditioning beyond the second order can be demonstrated by intermixing first-order trials with higher-order trials.
  判定：pass；C4 directly states that first-order trials are needed to periodically refresh original predictive relationships to demonstrate higher-order conditioning, which corresponds to intermixing first-order trials with higher-order trials.
  C4.text：First-order trials are needed to periodically refresh original predictive relationships to demonstrate higher-order conditioning
- R3 核心：Higher-order conditioning beyond the second order can also be demonstrated by providing a general energizing stimulus.
  判定：pass；C1 directly states that an energizing stimulus can enable higher-order conditioning beyond the second order under the right conditions, matching the requirement.
  C1.text：An energizing stimulus can enable higher-order conditioning beyond the second order under the right conditions

## KGGen / rl-qa-ch14-1

任务：t_b8c78333489c011dd2b1c5d0

Why, according to the chapter, is higher-order conditioning difficult to demonstrate above the second order, and under what circumstances can it still be shown?

旧：fail；核心：fail；完整：fail

- R1 核心：Higher-order conditioning is difficult to demonstrate above the second order because a higher-order reinforcer loses its reinforcing value, since during higher-order conditioning trials it is not repeatedly followed by the original US.
  判定：fail；The candidates only state that higher-order conditioning 'is rarely observed beyond Second-order conditioning' (C2), which is the observation but not the mechanism. No candidate explains the reason: that the higher-order reinforcer loses its reinforcing value because during higher-order trials it is not repeatedly followed by the original US.
  C2.text：higher-order conditioning is rarely observed beyond Second-order conditioning
- R2 核心：Under the right conditions, higher-order conditioning beyond the second order can be demonstrated by intermixing first-order trials with higher-order trials.
  判定：uncertain；C9 mentions that 'first-order trials refresh higher-order conditioning,' which is related to the idea of intermixing first-order trials. However, C9 does not explicitly state that this is a method for demonstrating conditioning beyond the second order, nor does it use the concept of 'intermixing.' The connection is plausible but not fully supported by the candidate text.
  C9.text：first-order trials refresh higher-order conditioning
- R3 核心：Higher-order conditioning beyond the second order can also be demonstrated by providing a general energizing stimulus.
  判定：fail；No candidate mentions a 'general energizing stimulus' or any equivalent concept that could demonstrate higher-order conditioning beyond the second order.

## 我们的方法（强化学习） / rl-qa-ch14-1

任务：t_bfbed90c62e7558264808f4a

Why, according to the chapter, is higher-order conditioning difficult to demonstrate above the second order, and under what circumstances can it still be shown?

旧：pass；核心：fail；完整：fail

- R1 核心：Higher-order conditioning is difficult to demonstrate above the second order because a higher-order reinforcer loses its reinforcing value, since during higher-order conditioning trials it is not repeatedly followed by the original US.
  判定：pass；C1 explicitly states that demonstrating higher-order conditioning is made difficult by extinction trials for the secondary reinforcer CS, because its predictive relationship to the US is disrupted. This captures the core idea that the higher-order reinforcer loses its reinforcing value since it is not being followed by the original US during higher-order trials.
  C1.text：Demonstrating higher-order conditioning is made difficult by the extinction trials that arise within higher-order conditioning sessions for the secondary reinforcer CS, because its predictive relationship to the US is disrupted
- R2 核心：Under the right conditions, higher-order conditioning beyond the second order can be demonstrated by intermixing first-order trials with higher-order trials.
  判定：pass；C1 directly states that the original predictive relationships 'must therefore be periodically refreshed by occasionally inserting first-order trials,' which corresponds to the requirement about intermixing first-order trials with higher-order trials to demonstrate conditioning beyond the second order.
  C1.text：the original predictive relationships must therefore be periodically refreshed by occasionally inserting first-order trials
- R3 核心：Higher-order conditioning beyond the second order can also be demonstrated by providing a general energizing stimulus.
  判定：fail；No candidate assertion mentions a 'general energizing stimulus' or any equivalent concept. C1 only discusses inserting first-order trials as a method to refresh the predictive relationship, but says nothing about an energizing stimulus. R3's required content is entirely absent from the candidate set.

## AutoSchemaKG / rl-qa-ch15-1

任务：t_35b796cce77dc8d5bf6e5f4f

In whose laboratory were the experiments that led to the reward prediction error hypothesis of dopamine neuron activity performed, and in what years were they carried out?

旧：pass；核心：pass；完整：pass

- R1 核心：The experiments were performed in the laboratory of neuroscientist Wolfram Schultz.
  判定：pass；C1's subject explicitly states the experiments were performed in the laboratory of Wolfram Schultz, supporting the requirement that the experiments were conducted in Wolfram Schultz's laboratory.
  C1.subject：The experiments that led to the reward prediction error hypothesis were performed in the 1980s and early 1990s in the laboratory of Wolfram Schultz.
- R2 核心：The experiments were carried out in the 1980s and early 1990s.
  判定：pass；C1's subject explicitly states the experiments were performed in the 1980s and early 1990s, directly matching the time period in the requirement.
  C1.subject：The experiments that led to the reward prediction error hypothesis were performed in the 1980s and early 1990s in the laboratory of Wolfram Schultz.

## GraphRAG / rl-qa-ch15-1

任务：t_a1cef822320ad5a033f46d6a

In whose laboratory were the experiments that led to the reward prediction error hypothesis of dopamine neuron activity performed, and in what years were they carried out?

旧：pass；核心：pass；完整：pass

- R1 核心：The experiments were performed in the laboratory of neuroscientist Wolfram Schultz.
  判定：pass；C1 has subject 'WOLFRAM SCHULTZ' and its text states 'The experiments in Schultz's laboratory...led to the hypothesis,' directly supporting that the experiments were performed in Wolfram Schultz's laboratory.
  C1.subject：WOLFRAM SCHULTZ
  C1.text：The experiments in Schultz's laboratory in the 1980s and early 1990s led to the hypothesis
- R2 核心：The experiments were carried out in the 1980s and early 1990s.
  判定：pass；C1 text explicitly states the experiments were 'in the 1980s and early 1990s,' directly matching the required time period.
  C1.text：The experiments in Schultz's laboratory in the 1980s and early 1990s led to the hypothesis

## KGGen / rl-qa-ch15-1

任务：t_186163075555ce8ef191ecad

In whose laboratory were the experiments that led to the reward prediction error hypothesis of dopamine neuron activity performed, and in what years were they carried out?

旧：fail；核心：fail；完整：fail

- R1 核心：The experiments were performed in the laboratory of neuroscientist Wolfram Schultz.
  判定：fail；No candidate assertion mentions Wolfram Schultz, his laboratory, or any researcher who performed the experiments. The candidates only discuss the reward prediction error hypothesis, dopamine neurons, TD errors, and a paper by Glimcher, P. W., but none identify the laboratory where the foundational experiments were performed.
- R2 核心：The experiments were carried out in the 1980s and early 1990s.
  判定：fail；No candidate assertion mentions the 1980s, early 1990s, or any time period during which the experiments were carried out. The candidates lack any temporal information about when the experiments took place.

## 我们的方法（强化学习） / rl-qa-ch15-1

任务：t_40d70dda0c3e6e54b556fa6c

In whose laboratory were the experiments that led to the reward prediction error hypothesis of dopamine neuron activity performed, and in what years were they carried out?

旧：fail；核心：fail；完整：fail

- R1 核心：The experiments were performed in the laboratory of neuroscientist Wolfram Schultz.
  判定：fail；No candidate mentions Wolfram Schultz or his laboratory. C5 mentions Montague, Dayan, and Sejnowski (1996), but these are authors of a theoretical paper, not the neuroscientist whose lab conducted the experiments. The candidates only discuss the hypothesis itself, not the experimental origin.
- R2 核心：The experiments were carried out in the 1980s and early 1990s.
  判定：fail；No candidate mentions the 1980s or early 1990s as the period when the experiments were carried out. C5 references 1996, but that is the year of the Montague, Dayan, and Sejnowski paper, not the time the experiments were performed.

## AutoSchemaKG / rl-qa-ch16-1

任务：t_bb90862894d69e148493cc74

In the personalized web services work of Li, Chu, Langford, and Schapire (2010), what was their objective and how much did their contextual bandit algorithm improve over a standard non-associative bandit algorithm?

旧：fail；核心：fail；完整：fail

- R1 核心：Their objective was to maximize the click-through rate (CTR) when personalizing the Yahoo! Front Page Today webpage, where CTR is defined as the ratio of the total number of clicks all users make on a webpage to the total number of visits to the page.
  判定：fail；Candidates C1 and C4 mention personalizing the Yahoo! Front Page Today webpage with a contextual bandit algorithm, but none of the candidates mention the objective of maximizing click-through rate (CTR) or provide the definition of CTR as the ratio of total clicks to total visits. The core content about CTR is entirely missing.
  C1.text：Li, Chu, Langford, and Schapire (2010) applied a contextual bandit algorithm to the problem of personalizing the Yahoo! Front Page Today webpage by selecting the news story to feature.
- R2 核心：Their contextual bandit algorithm improved over a standard non-associative bandit algorithm by 12.5%.
  判定：pass；C1 directly states that their contextual bandit algorithm improved over a standard non-associative bandit algorithm by 12.5%.
  C1.object：Their contextual bandit algorithm improved over a standard non-associative bandit algorithm by 12.5%.

## GraphRAG / rl-qa-ch16-1

任务：t_d22ec2f7fcff6f15b9b8be18

In the personalized web services work of Li, Chu, Langford, and Schapire (2010), what was their objective and how much did their contextual bandit algorithm improve over a standard non-associative bandit algorithm?

旧：pass；核心：fail；完整：fail

- R1 核心：Their objective was to maximize the click-through rate (CTR) when personalizing the Yahoo! Front Page Today webpage, where CTR is defined as the ratio of the total number of clicks all users make on a webpage to the total number of visits to the page.
  判定：fail；C3 confirms the objective was to maximize the click-through rate and C4 confirms the Yahoo! Front Page Today webpage, but no candidate assertion provides the definition of CTR as the ratio of total clicks to total visits. The definition portion of this requirement is not supported by any candidate.
- R2 核心：Their contextual bandit algorithm improved over a standard non-associative bandit algorithm by 12.5%.
  判定：pass；C3 explicitly states their algorithm improved by 12.5% over a standard bandit. In the context of comparing a contextual bandit against a 'standard bandit,' the standard bandit is understood as the non-associative (non-contextual) variant, which constitutes a direct semantic match with the requirement.
  C3.text：Their objective was to maximize the click-through rate, improving it by 12.5% over a standard bandit

## KGGen / rl-qa-ch16-1

任务：t_7b6cbfb2bf45b3c7759af39a

In the personalized web services work of Li, Chu, Langford, and Schapire (2010), what was their objective and how much did their contextual bandit algorithm improve over a standard non-associative bandit algorithm?

旧：fail；核心：fail；完整：fail

- R1 核心：Their objective was to maximize the click-through rate (CTR) when personalizing the Yahoo! Front Page Today webpage, where CTR is defined as the ratio of the total number of clicks all users make on a webpage to the total number of visits to the page.
  判定：fail；No candidate assertion mentions maximizing click-through rate (CTR), the Yahoo! Front Page Today webpage, or the definition of CTR. The candidates only state that the authors applied a contextual bandit algorithm and authored a paper, but lack the objective and CTR details.
- R2 核心：Their contextual bandit algorithm improved over a standard non-associative bandit algorithm by 12.5%.
  判定：fail；C1 confirms the contextual bandit algorithm improved over a non-associative bandit algorithm, but none of the candidates provide the specific 12.5% improvement figure.
  C1.text：contextual bandit algorithm improved over non-associative bandit algorithm

## 我们的方法（强化学习） / rl-qa-ch16-1

任务：t_8f47f3a5efa25c71a27834e7

In the personalized web services work of Li, Chu, Langford, and Schapire (2010), what was their objective and how much did their contextual bandit algorithm improve over a standard non-associative bandit algorithm?

旧：fail；核心：fail；完整：fail

- R1 核心：Their objective was to maximize the click-through rate (CTR) when personalizing the Yahoo! Front Page Today webpage, where CTR is defined as the ratio of the total number of clicks all users make on a webpage to the total number of visits to the page.
  判定：fail；C3 mentions contextual bandits enabling personalized web services with 'the objective of maximizing the total number of user clicks,' but it does not mention the Yahoo! Front Page Today webpage at all, and it does not define CTR as the ratio of total clicks to total visits. The candidate only refers to maximizing total clicks, which is not equivalent to maximizing a click-through rate ratio.
  C3.text：The 上下文赌博机 enables 个性化Web服务 by incorporating context consisting of features describing individual users and the content to be delivered, formalizing it as an associative reinforcement learning problem with the objective of maximizing the total number of user clicks.
- R2 核心：Their contextual bandit algorithm improved over a standard non-associative bandit algorithm by 12.5%.
  判定：fail；None of the candidate assertions mention a 12.5% improvement of the contextual bandit algorithm over a standard non-associative bandit algorithm. C7 only states that A/B testing is non-associative and does not personalize content delivery, but provides no quantitative improvement figure.
  C7.text：A/B testing is non-associative, like a 两臂赌博机问题（two-armed bandit problem）, and therefore this approach does not personalize content delivery.

## AutoSchemaKG / rl-qa-ch17-1

任务：t_23046d05d2d14f6f6a952994

What difficulties are noted for the inverse reinforcement learning approach, and what claim do Abbeel and Ng (2004) make despite those difficulties?

旧：pass；核心：uncertain；完整：fail

- R1 核心：逆强化学习方法无法精确完成，因为一个策略可能相对于多个不同的奖励信号都是最优的
  判定：pass；C6 明确说明一个策略可能相对于多个不同奖励信号是最优的，因此逆强化学习无法精确完成，直接支持该要点全部内容。
  C6.text：A policy can be optimal with respect to many different reward signals, so inverse reinforcement learning cannot be done exactly.
- R2 完整答案补充：例如，所有策略相对于一个常数奖励信号都是最优的（作为上述多解性的说明例子）
  判定：fail；没有候选提到“所有策略相对于一个常数奖励信号都是最优的”这一具体说明例子，C6 仅提到多个不同奖励信号的多解性，未涉及常数奖励信号。
- R3 核心：寻找合理奖励信号候选需要强假设，包括需要知道环境的动力学以及奖励信号为线性的特征向量
  判定：uncertain；C6 提到强假设需要知道环境的动力学和 feature vectors，但未明确说明“线性的（linear）”特征向量这一关键限定。强假设和环境动力学部分有支持，但线性特征向量这一必要细节缺失。
  C6.text：Strong assumptions are required for inverse reinforcement learning, including knowledge of the environment's dynamics and feature vectors.
  C2.text：Strong assumptions are required for inverse reinforcement learning.
- R4 核心：该方法还需要多次完全求解该问题（例如通过动态规划方法）
  判定：pass；C3 明确指出逆强化学习方法需要多次完全求解该问题，支持该要点核心内容。（动态规划方法的举例为辅助说明，核心信息已具备。）
  C3.text：The inverse reinforcement learning method requires completely solving the problem multiple times.
- R5 核心：尽管存在这些困难，Abbeel 和 Ng (2004) 仍然主张：在利用专家行为方面，逆强化学习方法有时比监督学习更有效
  判定：pass；C3 明确说明 Abbeel and Ng (2004) 主张逆强化学习方法在利用专家行为方面有时比监督学习更有效，完全覆盖该要点。C2 提供了更简略的支持。
  C3.text：Abbeel and Ng (2004) argue that the inverse reinforcement learning approach can sometimes be more effective than supervised learning for benefiting from expert behavior.

## GraphRAG / rl-qa-ch17-1

任务：t_b95b261f30ef03050760645e

What difficulties are noted for the inverse reinforcement learning approach, and what claim do Abbeel and Ng (2004) make despite those difficulties?

旧：fail；核心：fail；完整：fail

- R1 核心：逆强化学习方法无法精确完成，因为一个策略可能相对于多个不同的奖励信号都是最优的
  判定：fail；没有候选提及逆强化学习无法精确完成（多解性/一个策略可能相对于多个不同奖励信号都是最优的）这一困难。
- R2 完整答案补充：例如，所有策略相对于一个常数奖励信号都是最优的（作为上述多解性的说明例子）
  判定：fail；没有候选提及常数奖励信号作为多解性的说明例子。
- R3 核心：寻找合理奖励信号候选需要强假设，包括需要知道环境的动力学以及奖励信号为线性的特征向量
  判定：fail；没有候选提及寻找合理奖励信号所需的强假设（如环境动力学已知、奖励信号为线性的特征向量等）。
- R4 核心：该方法还需要多次完全求解该问题（例如通过动态规划方法）
  判定：pass；C7 明确说明逆强化学习方法需要多次完全求解该问题，例如通过动态规划方法。
  C7.text：The inverse reinforcement learning approach requires completely solving the problem multiple times, such as via dynamic programming methods
- R5 核心：尽管存在这些困难，Abbeel 和 Ng (2004) 仍然主张：在利用专家行为方面，逆强化学习方法有时比监督学习更有效
  判定：pass；C3 和 C10 明确指出 Abbeel 和 Ng 主张在利用专家行为方面，逆强化学习方法有时比监督学习更有效。
  C3.text：Abbeel and Ng argued that inverse reinforcement learning can sometimes be more effective than supervised learning for benefiting from expert behavior
  C10.text：Inverse reinforcement learning can sometimes be more effective than supervised learning for benefiting from the behavior of an expert

## KGGen / rl-qa-ch17-1

任务：t_c04cf6dc2f635286f233ec2f

What difficulties are noted for the inverse reinforcement learning approach, and what claim do Abbeel and Ng (2004) make despite those difficulties?

旧：fail；核心：fail；完整：fail

- R1 核心：逆强化学习方法无法精确完成，因为一个策略可能相对于多个不同的奖励信号都是最优的
  判定：fail；候选中没有断言说明逆强化学习无法精确完成是因为一个策略可能相对于多个不同的奖励信号都是最优的。C9仅涉及与监督学习的比较，未涉及多解性/非唯一性问题。
- R2 完整答案补充：例如，所有策略相对于一个常数奖励信号都是最优的（作为上述多解性的说明例子）
  判定：fail；候选中没有提到常数奖励信号使所有策略都是最优的这一具体说明例子。
- R3 核心：寻找合理奖励信号候选需要强假设，包括需要知道环境的动力学以及奖励信号为线性的特征向量
  判定：fail；C10支持了需要知道环境动力学这一部分，但缺少关于奖励信号需为线性特征向量的假设的候选证据。要点明确包含两个必要假设，缺少其中一个则不能通过。
  C10.object：environment's dynamics
- R4 核心：该方法还需要多次完全求解该问题（例如通过动态规划方法）
  判定：uncertain；C8支持逆强化学习方法需要动态规划方法，但未明确提到需要多次完全求解该问题。'多次'这一关键限定无法从候选中确认。
  C8.object：dynamic programming methods
- R5 核心：尽管存在这些困难，Abbeel 和 Ng (2004) 仍然主张：在利用专家行为方面，逆强化学习方法有时比监督学习更有效
  判定：pass；C1将Abbeel和Ng (2004)与逆强化学习观点关联，C9明确断言逆强化学习方法比监督学习更有效。组合起来支持'Abbeel和Ng主张逆强化学习在利用专家行为方面比监督学习更有效'这一核心论断。
  C1.text：Abbeel and Ng (2004) argue about inverse reinforcement learning approach
  C9.text：inverse reinforcement learning approach is more effective than Supervised learning

## 我们的方法（强化学习） / rl-qa-ch17-1

任务：t_1d80e5c9cf9ea52beca73776

What difficulties are noted for the inverse reinforcement learning approach, and what claim do Abbeel and Ng (2004) make despite those difficulties?

旧：fail；核心：fail；完整：fail

- R1 核心：逆强化学习方法无法精确完成，因为一个策略可能相对于多个不同的奖励信号都是最优的
  判定：pass；C3 states exact recovery is impossible because a policy can be optimal with respect to many different reward signals.
  C3.text：exact recovery is impossible because a policy can be optimal with respect to many different 奖励（强化学习）s
- R2 完整答案补充：例如，所有策略相对于一个常数奖励信号都是最优的（作为上述多解性的说明例子）
  判定：pass；C3 explicitly provides the constant reward signal example to illustrate the multiple-solution issue.
  C3.text：for example, all policies are optimal with respect to a constant reward signal
- R3 核心：寻找合理奖励信号候选需要强假设，包括需要知道环境的动力学以及奖励信号为线性的特征向量
  判定：pass；C1 describes the strong assumptions needed, including knowledge of the environment's dynamics and linearity of the reward signal in the feature vectors.
  C1.text：requires strong assumptions (including knowledge of the environment's dynamics and of the feature vectors in which the reward signal is linear)
- R4 核心：该方法还需要多次完全求解该问题（例如通过动态规划方法）
  判定：pass；C1 states the approach requires completely solving the problem (e.g., by dynamic programming methods) multiple times.
  C1.text：requires completely solving the problem (e.g., by dynamic programming methods) multiple times
- R5 核心：尽管存在这些困难，Abbeel 和 Ng (2004) 仍然主张：在利用专家行为方面，逆强化学习方法有时比监督学习更有效
  判定：fail；No candidate asserts that Abbeel and Ng (2004) claim inverse reinforcement learning is sometimes more effective than supervised learning for leveraging expert behavior. C1 mentions that IRL can be used to find plausible reward-signal candidates from expert behavior, but does not draw a comparison to supervised learning or make a superiority claim.
