from promptsource.templates import Template


PROMPTS = {
    'system': 'You are an automated program repair tool.',
    'system_decide_cs': 'You are an automated program repair tool. Your response should follow the required json format', 
    'system_decide': 'You are an expert program repair system. You need to analyze the given bug and decide which programming language to translate it to for the next repair iteration. Base your decision on the provided historical repair data. You should make the analysis step by step. The output must be in the required json format.', 
    'apr': "Fix a buggy program written in {{lang_cluster}} language to solve the following programming problem:\nDescription: {{prob_desc_description}}\nInput Specification: {{prob_desc_input_spec}}\nOutput Specification: {{prob_desc_output_spec}}\n{% for input, output in zip(prob_desc_sample_inputs, prob_desc_sample_outputs) %}\nSample Input:\n{{input}}\nSample Output:\n{{output}}\n{% endfor %}\nNotes: {{prob_desc_notes}}\nTake input from {{prob_desc_input_from}} and output to {{prob_desc_output_to}}\n\nHere is the code with a bug of {{bug_exec_outcome}}:\n\n{{bug_source_code}}\n\nProvide the fixed {{lang_cluster}} code without any description or extra tokens.\n\nFixed source code:\n ||END-of-SRC|| ",
    'apr-hist': "Fix a buggy program written in {{lang_cluster}} language to solve the following programming problem:\nDescription: {{prob_desc_description}}\nInput Specification: {{prob_desc_input_spec}}\nOutput Specification: {{prob_desc_output_spec}}\n{% for input, output in zip(prob_desc_sample_inputs, prob_desc_sample_outputs) %}\nSample Input:\n{{input}}\nSample Output:\n{{output}}\n{% endfor %}\nNotes: {{prob_desc_notes}}\nTake input from {{prob_desc_input_from}} and output to {{prob_desc_output_to}}\n\nHere is the code with a bug of {{bug_exec_outcome}}:\n\n{{bug_source_code}}\n{{repair_hist}}\nProvide the fixed {{lang_cluster}} code without any description or extra tokens.\n\nFixed source code:\n ||END-of-SRC|| ", 
    'language_decision': 'Current Bug Information:\n{{bug_info}}\n\nHistorical Repair Data:\n{{history}}\n\nScope of Target Languages: {{scope}}\n\nPreviously Attempted Languages: {{attempted}}\n\nTask Description: The task is to translate the bugs that cannot be fixed in one programming language to another programming language and then try to fix it. You need to analyze the current bug and decide which programming language to translate it to for the next repair iteration. Base your decision on the provided historical repair data. Initially, the historical data includes previous repair attempts for bugs similar to the current bug. After the initial iteration, the historical translation-repair attempts will also be added to the historical repair data for you to analyze.\n- Consider factors such as:\n    - Bug similarity.\n    - Repair language.\n    - pass@10 scores.\n- Provide a justification for your decision step by step.\n\nConstraints:\n- The target language you select must be within the scope of target languages.\n- Previously attempted languages cannot be used again.\n\nOutput Format (json):\n```json{"Target Language": "Your recommended language", "Justification": "Your reasoning"}```\n\nYou should follow the output format without extra tokens. Your response:\n||END-of-SRC|| ',
    'nohist': 'There is buggy code in {{lang}} language.\n\nScope of Target Languages: {{scope}}\n\nPreviously Attempted Languages: {{attempted}}\n\nTask Description: The task is to translate the bugs that cannot be fixed in one programming language to another programming language and then try to fix it. You need to decide which programming language to translate it to for the next repair iteration. \n- Provide a justification for your decision step by step.\n\nConstraints:\n- The target language you select must be within the scope of target languages.\n- Previously attempted languages cannot be used again.\n\nOutput Format:\n- Target Language: [Your recommended language]\n- Justification: [Your reasoning]||END-of-SRC|| ',
    'translation': 'Here is code in {{source_lang}} programming lanaguge. Translate the following code from {{source_lang}} to {{target_lang}} programming lanaguge. Do not output any extra description or tokens other than the translated code. \n\n{{bug_source_code}}||END-of-SRC|| ',
    'back_translation': 'Here is code in {{target_lang}} programming lanaguge. Translate the following code from {{target_lang}} to {{source_lang}} programming lanaguge. Do not output any extra description or tokens other than the translated code. \n\n{{bug_source_code}}||END-of-SRC|| ',
    'planning': '',
    'implement': ''

}

FEW_SHOT_SP = '''
Below are some few-shot examples for planning bug fixes:

[Problem 1]
Fix a buggy program written in C++ language to solve the following programming problem:
Description: Arpa has found a list containing n numbers. He calls a list bad if and only if it is not empty and gcd (see notes section for more information) of numbers in the list is 1.Arpa can perform two types of operations:  Choose a number and delete it with cost x.  Choose a number and increase it by 1 with cost y. Arpa can apply these operations to as many numbers as he wishes, and he is allowed to apply the second operation arbitrarily many times on the same number.Help Arpa to find the minimum possible cost to make the list good.
Input Specification: First line contains three integers n, x and y (1 ≤ n ≤ 5·105, 1 ≤ x, y ≤ 109) — the number of elements in the list and the integers x and y. Second line contains n integers a1, a2, ..., an (1 ≤ ai ≤ 106) — the elements of the list.
Output Specification: Print a single integer: the minimum possible cost to make the list good.

Sample Input:
4 23 17
1 17 17 16
Sample Output:
40

Sample Input:
10 6 2
100 49 71 73 66 96 8 60 41 63
Sample Output:
10

Notes: NoteIn example, number 1 must be deleted (with cost 23) and number 16 must increased by 1 (with cost 17).A gcd (greatest common divisor) of a set of numbers is the maximum integer that divides all integers in the set. Read more about gcd here.
Take input from standard input and output to standard output

Here is the code with a bug of COMPILATION_ERROR:

//in the name of Allah
#include <bits/stdc++.h>
using namespace std ;
#define F first
#define S second
typedef long long ll ;
const ll INF = 1<<30 ;
const ll N = (1e6)+17 ;
ll n , a[N] , sum[4*N] , qu[N] , ans = INF , x , y ;
map<ll,ll> vo ;
int main()
{
std::ios::sync_with_stdio(0) ;
cin.tie(0) ;
cout.tie(0);
cin >> n >> x >> y ;
ll maxx=0 , minn=INF ;
for(int i = 0 ; i< n  ; i++){
    cin >> a[i] ;
    vo[a[i]] ++ ;
    maxx = max(maxx , a[i]) ;
    minn = min(minn , a[i]) ;
}
if(v[1]==1)qu[1] = sum[1] = 1  ;
for(int i = 2 ; i <= N ; i ++){
  sum[i] = sum[i-1] + (vo[i]*i) ;
  qu[i] = qu[i-1] + vo[i] ;
}
ll m = (x/y)+(x%y!=0) ;
for(int i = 1 ; i <= N ; i ++ ){
    ll anss = 0 ;
     for(int j = i ; j <= N ; j += i){
        if(m>=(i-1))anss += y*((j*(qu[j]-qu[j-i]))-(sum[j]-sum[j-i])) ;
        else{
            anss += x*(qu[j-m-1]-qu[j-i]) ;
            anss += y*((j*(qu[j]-qu[j-m-1]))-(sum[j]-sum[j-m-1])) ;
        }
    }
    if(anss > 0 )ans = min(ans , anss) ;
}
cout << ans ;
return 0 ;
}

[Plan 1]
1.Remove the undefined map variable v and replace with the defined vo map.
2.Fix the initialization and size of arrays to prevent overflow.
3.Modify the array pre-computation logic to correctly calculate prefix sums.
4.Restructure the main calculation loop to handle GCD checking properly.
5.Add boundary check for array indices to prevent out-of-bounds access.
6.Update the formula for calculating the cost of operations.
7.Initialize the answer variable with a reasonable upper bound.
8.Set a proper termination condition for the inner loop to improve efficiency.

[Problem 2]
Fix a buggy program written in Rust language to solve the following programming problem:
Description: Recently, Mike was very busy with studying for exams and contests. Now he is going to chill a bit by doing some sight seeing in the city.City consists of n intersections numbered from 1 to n. Mike starts walking from his house located at the intersection number 1 and goes along some sequence of intersections. Walking from intersection number i to intersection j requires |i - j| units of energy. The total energy spent by Mike to visit a sequence of intersections p1 = 1, p2, ..., pk is equal to  units of energy.Of course, walking would be boring if there were no shortcuts. A shortcut is a special path that allows Mike walking from one intersection to another requiring only 1 unit of energy. There are exactly n shortcuts in Mike's city, the ith of them allows walking from intersection i to intersection ai (i ≤ ai ≤ ai + 1) (but not in the opposite direction), thus there is exactly one shortcut starting at each intersection. Formally, if Mike chooses a sequence p1 = 1, p2, ..., pk then for each 1 ≤ i &lt; k satisfying pi + 1 = api and api ≠ pi Mike will spend only 1 unit of energy instead of |pi - pi + 1| walking from the intersection pi to intersection pi + 1. For example, if Mike chooses a sequence p1 = 1, p2 = ap1, p3 = ap2, ..., pk = apk - 1, he spends exactly k - 1 units of total energy walking around them.Before going on his adventure, Mike asks you to find the minimum amount of energy required to reach each of the intersections from his home. Formally, for each 1 ≤ i ≤ n Mike is interested in finding minimum possible total energy of some sequence p1 = 1, p2, ..., pk = i.
Input Specification: The first line contains an integer n (1 ≤ n ≤ 200 000) — the number of Mike's city intersection. The second line contains n integers a1, a2, ..., an (i ≤ ai ≤ n , , describing shortcuts of Mike's city, allowing to walk from intersection i to intersection ai using only 1 unit of energy. Please note that the shortcuts don't allow walking in opposite directions (from ai to i).
Output Specification: In the only line print n integers m1, m2, ..., mn, where mi denotes the least amount of total energy required to walk from intersection 1 to intersection i.

Sample Input:
3
2 2 3
Sample Output:
0 1 2

Sample Input:
5
1 2 3 4 5
Sample Output:
0 1 2 3 4

Sample Input:
7
4 4 4 4 7 7 7
Sample Output:
0 1 2 1 2 3 3

Notes: NoteIn the first sample case desired sequences are:1: 1; m1 = 0;2: 1, 2; m2 = 1;3: 1, 3; m3 = |3 - 1| = 2.In the second sample case the sequence for any intersection 1 &lt; i is always 1, i and mi = |1 - i|.In the third sample case — consider the following intersection sequences:1: 1; m1 = 0;2: 1, 2; m2 = |2 - 1| = 1;3: 1, 4, 3; m3 = 1 + |4 - 3| = 2;4: 1, 4; m4 = 1;5: 1, 4, 5; m5 = 1 + |4 - 5| = 2;6: 1, 4, 6; m6 = 1 + |4 - 6| = 3;7: 1, 4, 5, 7; m7 = 1 + |4 - 5| + 1 = 3.
Take input from standard input and output to standard output

Here is the code with a bug of WRONG_ANSWER:

use std::io::BufRead;

#[derive(Clone,Debug)]
struct Problem {
    input: Vec<u32>,
}

fn read_problem<R: BufRead>(br: R) -> Problem {
    let mut lines = br.lines().map(Result::unwrap);

    let ct = str::parse(&lines.next().unwrap()).unwrap();
    let input = lines.next().unwrap().split_whitespace()
        .map(|w| str::parse::<u32>(w).unwrap())
        .map(|n| n - 1)
        .collect::<Vec<_>>();
    assert!(lines.next().is_none());
    assert!(input.len() == ct);
    Problem { input: input }
}

fn solve(problem: Problem) -> Vec<u32> {
    let mut best = problem.input.iter().map(|_| u32::max_value()).collect::<Vec<_>>();
    let mut next = 0;
    for (i, ai) in problem.input.into_iter().enumerate() {
        if next < best[i] {
            best[i] = next;
        }
        next = best[i] + 1;
        if next < best[ai as usize] {
            best[ai as usize] = next;
        }
    }
    best
}

fn main() {
    let stdin = std::io::stdin();
    let p = read_problem(stdin.lock());
    for k in solve(p) {
        print!("{} ", k);
    }
    println!("");
}

[Plan 2]
1.Replace the linear traversal algorithm with a breadth-first search approach.
2.Initialize a queue to track intersections to visit with their associated costs.
3.Change the next variable from a single value to a vector of positions to explore.
4.Implement a while loop to process all positions in the queue at each cost level.
5.Add logic to explore adjacent intersections (n-1 and n+1) when updating costs.
6.Include the shortcut destination in the next positions to explore.
7.Use std::mem::replace to efficiently swap out the processed queue.
8.Increment the cost after processing all intersections at the current cost level.
9.Add boundary checks when adding new positions to prevent out-of-bounds errors.

[Problem 3]
Fix a buggy program written in Go language to solve the following programming problem:
Description: You are given a sequence of integers of length $$$n$$$ and integer number $$$k$$$. You should print any integer number $$$x$$$ in the range of $$$[1; 10^9]$$$ (i.e. $$$1 \le x \le 10^9$$$) such that exactly $$$k$$$ elements of given sequence are less than or equal to $$$x$$$.Note that the sequence can contain equal elements.If there is no such $$$x$$$, print "-1" (without quotes).
Input Specification: The first line of the input contains integer numbers $$$n$$$ and $$$k$$$ ($$$1 \le n \le 2 \cdot 10^5$$$, $$$0 \le k \le n$$$). The second line of the input contains $$$n$$$ integer numbers $$$a_1, a_2, \dots, a_n$$$ ($$$1 \le a_i \le 10^9$$$) — the sequence itself.
Output Specification: Print any integer number $$$x$$$ from range $$$[1; 10^9]$$$ such that exactly $$$k$$$ elements of given sequence is less or equal to $$$x$$$. If there is no such $$$x$$$, print "-1" (without quotes).

Sample Input:
7 4
3 7 5 1 10 3 20
Sample Output:
6

Sample Input:
7 2
3 7 5 1 10 3 20
Sample Output:
-1

Notes: NoteIn the first example $$$5$$$ is also a valid answer because the elements with indices $$$[1, 3, 4, 6]$$$ is less than or equal to $$$5$$$ and obviously less than or equal to $$$6$$$.In the second example you cannot choose any number that only $$$2$$$ elements of the given sequence will be less than or equal to this number because $$$3$$$ elements of the given sequence will be also less than or equal to this number.
Take input from standard input and output to standard output

Here is the code with a bug of RUNTIME_ERROR:


package main

import (
	"fmt"
	"sort"
)

func main() {
	var n, k int
	var res int
	_, err := fmt.Scan(&n, &k)
	if err != nil {
		fmt.Println(err)
	} else {
		seq := make([]int, n)
		for i := 0; i < n; i++ {
			_, err := fmt.Scan(&seq[i])
			if err != nil {
				fmt.Println(err)
			}
		}
		sort.Ints(seq)
		if k == n {
			res = seq[k-1]
		} else {
			if seq[k-1] == seq[k] {
				res = -1
			} else {
				res = seq[k-1]
			}
		}
	}
	fmt.Println(res)
}

[Plan 3]
1.Replace standard input scanning with buffered input to handle larger inputs.
2.Add a special case for when k equals 0 (boundary condition).
3.Handle the case where k is 0 by selecting one less than the smallest element.
4.Check if the smallest element is already 1 when k is 0, and return -1 if true.
5.Fix array access for the boundary case when k equals n.
6.Use len(seq)-1 to access the last element safely.
7.Add bounds checking before accessing seq[k] to prevent out-of-bounds errors.
8.Properly handle error conditions throughout the code.
9.Use Fscan instead of Scan for more efficient input parsing.

[Problem 4]
Fix a buggy program written in Python language to solve the following programming problem:
Description: You have array of $$$n$$$ numbers $$$a_{1}, a_{2}, \ldots, a_{n}$$$. Rearrange these numbers to satisfy $$$|a_{1} - a_{2}| \le |a_{2} - a_{3}| \le \ldots \le |a_{n-1} - a_{n}|$$$, where $$$|x|$$$ denotes absolute value of $$$x$$$. It's always possible to find such rearrangement.Note that all numbers in $$$a$$$ are not necessarily different. In other words, some numbers of $$$a$$$ may be same.You have to answer independent $$$t$$$ test cases.
Input Specification: The first line contains a single integer $$$t$$$ ($$$1 \le t \le 10^{4}$$$) — the number of test cases. The first line of each test case contains single integer $$$n$$$ ($$$3 \le n \le 10^{5}$$$) — the length of array $$$a$$$. It is guaranteed that the sum of values of $$$n$$$ over all test cases in the input does not exceed $$$10^{5}$$$. The second line of each test case contains $$$n$$$ integers $$$a_{1}, a_{2}, \ldots, a_{n}$$$ ($$$-10^{9} \le a_{i} \le 10^{9}$$$).
Output Specification: For each test case, print the rearranged version of array $$$a$$$ which satisfies given condition. If there are multiple valid rearrangements, print any of them.

Sample Input:
2
6
5 -2 4 8 6 5
4
8 1 4 2
Sample Output:
5 5 4 6 8 -2
1 2 4 8

Notes: NoteIn the first test case, after given rearrangement, $$$|a_{1} - a_{2}| = 0 \le |a_{2} - a_{3}| = 1 \le |a_{3} - a_{4}| = 2 \le |a_{4} - a_{5}| = 2 \le |a_{5} - a_{6}| = 10$$$. There are other possible answers like "5 4 5 6 -2 8".In the second test case, after given rearrangement, $$$|a_{1} - a_{2}| = 1 \le |a_{2} - a_{3}| = 2 \le |a_{3} - a_{4}| = 4$$$. There are other possible answers like "2 4 8 1".
Take input from standard input and output to standard output

Here is the code with a bug of TIME_LIMIT_EXCEEDED:

t = int(input())

for _ in range(t):
	n = map(int,input())
	array = list(map(int,input().split()))
	array.sort()

	out = []

	while len(array) > 1:

		out += [array[0],array[-1]]
		array = array[1:-1]

	out += array

	print(*out[::-1])

[Plan 4]
1.Fix the parsing of n by converting it to a single integer.
2.Create a new approach that avoids modifying the original array in each iteration.
3.Process the sorted array in a single pass rather than repeatedly slicing it.
4.Create a new output array by alternating elements from the beginning and end.
5.Handle odd-length arrays by adding the middle element at the end.
6.Process only half of the array elements in the while loop to avoid duplication.
7.Use array indexing instead of repeatedly removing elements.
8.Separate the input array from the output array to maintain clarity.
9.Reverse the final result before printing to maintain the required ordering.

[Problem 5]
Fix a buggy program written in Java language to solve the following programming problem:
Description: Welcome to Innopolis city. Throughout the whole year, Innopolis citizens suffer from everlasting city construction. From the window in your room, you see the sequence of n hills, where i-th of them has height ai. The Innopolis administration wants to build some houses on the hills. However, for the sake of city appearance, a house can be only built on the hill, which is strictly higher than neighbouring hills (if they are present). For example, if the sequence of heights is 5, 4, 6, 2, then houses could be built on hills with heights 5 and 6 only.The Innopolis administration has an excavator, that can decrease the height of an arbitrary hill by one in one hour. The excavator can only work on one hill at a time. It is allowed to decrease hills up to zero height, or even to negative values. Increasing height of any hill is impossible. The city administration wants to build k houses, so there must be at least k hills that satisfy the condition above. What is the minimum time required to adjust the hills to achieve the administration's plan?However, the exact value of k is not yet determined, so could you please calculate answers for all k in range ? Here  denotes n divided by two, rounded up.
Input Specification: The first line of input contains the only integer n (1 ≤ n ≤ 5000)—the number of the hills in the sequence. Second line contains n integers ai (1 ≤ ai ≤ 100 000)—the heights of the hills in the sequence.
Output Specification: Print exactly  numbers separated by spaces. The i-th printed number should be equal to the minimum number of hours required to level hills so it becomes possible to build i houses.

Sample Input:
5
1 1 1 1 1
Sample Output:
1 2 2

Sample Input:
3
1 2 3
Sample Output:
0 2

Sample Input:
5
1 2 3 2 2
Sample Output:
0 1 3

Notes: NoteIn the first example, to get at least one hill suitable for construction, one can decrease the second hill by one in one hour, then the sequence of heights becomes 1, 0, 1, 1, 1 and the first hill becomes suitable for construction.In the first example, to get at least two or at least three suitable hills, one can decrease the second and the fourth hills, then the sequence of heights becomes 1, 0, 1, 0, 1, and hills 1, 3, 5 become suitable for construction.
Take input from standard input and output to standard output

Here is the code with a bug of MEMORY_LIMIT_EXCEEDED:

import java.io.OutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.PrintWriter;
import java.util.Arrays;
import java.util.InputMismatchException;
import java.io.IOException;
import java.io.InputStream;

/**
 * Built using CHelper plug-in
 * Actual solution is at the top
 */
public class Main {
    public static void main(String[] args) {
        InputStream inputStream = System.in;
        OutputStream outputStream = System.out;
        MyScan in = new MyScan(inputStream);
        PrintWriter out = new PrintWriter(outputStream);
        TaskC solver = new TaskC();
        solver.solve(1, in, out);
        out.close();
    }

    static class TaskC {
        public void solve(int testNumber, MyScan in, PrintWriter out) {
            int n = in.nextInt();
            int[] data = new int[n + 2];
            for (int s = 0; s < n; s++) {
                data[s + 1] = in.nextInt();
            }
            if (n == 1) {
                out.println(0);
                return;
            }
            int[][] next = new int[n + 2][3];

            for (int s = 2; s < n; s++) {
                next[s][0] = data[s];
                next[s][1] = Math.min(data[s - 1] - 1, data[s]);
                next[s][2] = Math.min(data[s + 1] - 1, data[s]);
                Arrays.sort(next[s], 1, 3);
                if (next[s][1] == next[s][2] || next[s][0] == next[s][2]) {
                    next[s] = Arrays.copyOf(next[s], 2);
                }
                if (next[s][1] == next[s][0]) {
                    next[s] = Arrays.copyOf(next[s], 1);
                }
            }
            next[0] = new int[]{0};
            next[n + 1] = new int[]{0};
            next[1] = new int[]{data[1], Math.min(data[2] - 1, data[1])};
            next[n] = new int[]{data[n], Math.min(data[n - 1] - 1, data[n])};


            long[][][] nn = new long[n + 1][9][(n + 3) / 2];
            for (long[][] m : nn) {
                for (long[] m1 : m) {
                    Arrays.fill(m1, 1_000_000_000_000L);
                }
            }

            nn[0][0][0] = 0;
            nn[0][1][0] = data[1] - next[1][1];


            for (int x = 0; x < n; x++) {
                for (int i1 = 0; i1 < next[x].length; i1++) {
                    int i = i1 * 3;
                    for (int i2 = 0; i2 < next[x + 1].length; i2++, i++) {
                        for (int moves = 0; moves < (n + 1) / 2; moves++) {
                            if (nn[x][i][moves] == 1_000_000_000_000_000L) continue;
                            for (int curIndex = 0; curIndex < next[x + 2].length; curIndex++) {
                                int tarMoves = moves;
                                if (next[x + 1][i2] > next[x][i1] && next[x + 1][i2] > next[x + 2][curIndex]) {
                                    tarMoves++;
                                }
                                nn[x + 1][(i2 * 3) + curIndex][tarMoves] = Math.min(nn[x + 1][(i2 * 3) + curIndex][tarMoves], nn[x][i][moves] + next[x + 2][0] - next[x + 2][curIndex]);
                            }
                        }
                    }
                }
            }
            long[] a = new long[nn[n][0].length];
            Arrays.fill(a, Long.MAX_VALUE);
            for (int s = 0; s < 9; s++) {
                for (int l = 0; l < nn[n][0].length; l++) {
                    a[l] = Math.min(a[l], nn[n][s][l]);
                }
            }
            for (int s = nn[n][0].length - 1; s > 0; s--) {
                a[s - 1] = Math.min(a[s - 1], a[s]);
            }
            for (int l = 1; l <= (n + 1) / 2; l++) {
                out.print(a[l] + " ");
            }

        }

    }

    static class MyScan {
        private final InputStream in;
        private byte[] inbuf = new byte[1024];
        public int lenbuf = 0;
        public int ptrbuf = 0;

        public MyScan(InputStream in) {
            this.in = in;
        }

        private int readByte() {
            if (lenbuf == -1) throw new InputMismatchException();
            if (ptrbuf >= lenbuf) {
                ptrbuf = 0;
                try {
                    lenbuf = in.read(inbuf);
                } catch (IOException e) {
                    throw new InputMismatchException();
                }
                if (lenbuf <= 0) return -1;
            }
            return inbuf[ptrbuf++];
        }

        public int nextInt() {
            int num = 0, b;
            boolean minus = false;
            while ((b = readByte()) != -1 && !((b >= '0' && b <= '9') || b == '-')) ;
            if (b == '-') {
                minus = true;
                b = readByte();
            }

            while (true) {
                if (b >= '0' && b <= '9') {
                    num = num * 10 + (b - '0');
                } else {
                    return minus ? -num : num;
                }
                b = readByte();
            }
        }

    }
}

[Plan 5]
1.Implement a memory-efficient approach using the cache design pattern with only two arrays instead of n+1 arrays.
2.Add a class-level cache variable to store only the current and previous states.
3.Create an ind variable to track which array in the cache is currently active.
4.Implement a helper method `nv()` to get a new initialized array and toggle between the two arrays.
5.Replace the large 3D array (long[][][]) with a smaller 3D array (int[][][]) to reduce memory usage.
6.Use a fixed initialization value of 1_000_000_000 instead of 1_000_000_000_000L.
7.Fix the boundary check for continuing on large values in the inner loop.
8.Optimize the nested loops to avoid recalculating indices.
9.Improve memory usage by reusing arrays instead of creating new ones in each iteration.
10.Replace the array access pattern in the final calculations to iterate through all arrays.
11.Use early termination conditions to avoid unnecessary calculations.
12.Implement proper cache initialization inside the `nv()` method.

Here is the problem that needs a fixing plan:

Fix a buggy program written in {{lang_cluster}} language to solve the following programming problem:
Description: {{prob_desc_description}}
Input Specification: {{prob_desc_input_spec}}
Output Specification: {{prob_desc_output_spec}}
{% for input, output in zip(prob_desc_sample_inputs, prob_desc_sample_outputs) %}
Sample Input:
{{input}}
Sample Output:
{{output}}
{% endfor %}
Notes: {{prob_desc_notes}}
Take input from {{prob_desc_input_from}} and output to {{prob_desc_output_to}}

Here is the code with a bug of {{bug_exec_outcome}}:

{{bug_source_code}}

Provide a fixing plan for the problem without any description or extra tokens.
 ||END-of-SRC|| 
'''


IMPLEMENTATION = '''
Fix a buggy program written in {{lang_cluster}} language to solve the following programming problem:
Description: {{prob_desc_description}}
Input Specification: {{prob_desc_input_spec}}
Output Specification: {{prob_desc_output_spec}}
{% for input, output in zip(prob_desc_sample_inputs, prob_desc_sample_outputs) %}
Sample Input:
{{input}}
Sample Output:
{{output}}
{% endfor %}
Notes: {{prob_desc_notes}}
Take input from {{prob_desc_input_from}} and output to {{prob_desc_output_to}}

Here is the code with a bug of {{bug_exec_outcome}}:

{{bug_source_code}}

Here is the plan to fix the code:
{{plan}}

Provide the fixed {{lang_cluster}} code following the plan without any description or extra tokens.

Fixed source code:

 ||END-of-SRC|| 
'''

def apr(dt):
    tpl = Template("apr", PROMPTS['apr'], "xCodeEval", delimeter="||END-of-SRC||")
    prompt_text = tpl.apply(dt)
    return prompt_text

def apr_hist(dt):
    tpl = Template("apr-hist", PROMPTS['apr-hist'], "xCodeEval", delimeter="||END-of-SRC||")
    prompt_text = tpl.apply(dt)
    return prompt_text

def plan(dt):
    tpl = Template("plan", FEW_SHOT_SP, "xCodeEval", delimeter="||END-of-SRC||")
    prompt_text = tpl.apply(dt)
    return prompt_text

def imp(dt):
    tpl = Template("implementation", IMPLEMENTATION, "xCodeEval", delimeter="||END-of-SRC||")
    prompt_text = tpl.apply(dt)
    return prompt_text

def decision(bug_retrieval):
    tpl = Template("decision", PROMPTS['language_decision'], "xCodeEval", delimeter="||END-of-SRC||")
    prompt_text = tpl.apply(bug_retrieval)
    return prompt_text

def nohist(bug_retrieval):
    tpl = Template("decision_nohist", PROMPTS['nohist'], "xCodeEval", delimeter="||END-of-SRC||")
    prompt_text = tpl.apply(bug_retrieval)
    return prompt_text

def trans(dt):
    tpl = Template("trans", PROMPTS['translation'], "xCodeEval", delimeter="||END-of-SRC||")
    prompt_text = tpl.apply(dt)
    return prompt_text

def back_trans(dt):
    tpl = Template("backtrans", PROMPTS['back_translation'], "xCodeEval", delimeter="||END-of-SRC||")
    prompt_text = tpl.apply(dt)
    return prompt_text
