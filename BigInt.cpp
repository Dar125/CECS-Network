// Muhammad Dar
// CECS-325-01
// Prog-6 BigInt
// 05/08/2024
// I certify that this program is my own orginal work. I did not copy any part of this program from
// any other source. I further certify that I typed each and every line of code in this program.

#include <iostream>
#include <iomanip>
#include <vector>
#include <string>
#include <cmath>
#include <limits.h>
#include <ctime>
#include <cstdlib>

using namespace std;

// Class definition for big integers arithmetic
class BigInt {
private:
    vector<char> vi; // vector to store digits

public:
    // Constructors
    BigInt();
    BigInt(int);
    BigInt(string);

    // Overloaded operators
    BigInt operator+(const BigInt&) const;
    BigInt operator-(const BigInt&) const;
    BigInt operator*(const BigInt&) const;
    BigInt operator/(const BigInt&) const;
    BigInt operator%(const BigInt&) const;
    BigInt operator++(int);
    BigInt operator++();
    bool operator==(const BigInt&) const;
    bool operator<=(const BigInt&) const;

    // Member functions
    void print() const;
    int size() const;
    BigInt fibo() const;
    BigInt fact() const;

private:
    // Helper function for Fibonacci computation
    BigInt fiboHelper(BigInt, BigInt, BigInt) const;
};

// Default constructor
BigInt::BigInt() {}

// Constructor from integer
BigInt::BigInt(int n) {
    while (n > 0) {
        vi.push_back(n % 10);
        n /= 10;
    }
}
// Constructor for string
BigInt::BigInt(string s) {
    for (int i = s.length() - 1; i >= 0; i--) {
        vi.push_back(s[i] - '0');
    }
}

// Addition operator
BigInt BigInt::operator+(const BigInt& other) const {
    BigInt result;
    int carry = 0;
    int maxSize = max(vi.size(), other.vi.size());
    
    for (int i = 0; i < maxSize || carry; i++) {
        if (i == result.size())
            result.vi.push_back(0);
        
        int sum = carry + (i < vi.size() ? vi[i] : 0) + (i < other.vi.size() ? other.vi[i] : 0);
        result.vi[i] = sum % 10;
        carry = sum / 10;
    }
    
    return result;
}

// Subtraction operator
BigInt BigInt::operator-(const BigInt& other) const {
    BigInt result;
    int borrow = 0;
    for (int i = 0; i < vi.size(); i++) {
        int sub = vi[i] - borrow - (i < other.vi.size() ? other.vi[i] : 0);
        if (sub < 0) {
            sub += 10;
            borrow = 1;
        } else {
            borrow = 0;
        }
        result.vi.push_back(sub);
    }
    while (!result.vi.empty() && result.vi.back() == 0)
        result.vi.pop_back();
    return result;
}

// Multiplication operator
BigInt BigInt::operator*(const BigInt& other) const {
    BigInt result;
    result.vi.resize(vi.size() + other.vi.size());
    for (int i = 0; i < vi.size(); i++) {
        int carry = 0;
        for (int j = 0; j < other.vi.size() || carry; j++) {
            long long sum = result.vi[i+j] + carry + vi[i] * 1LL * (j < other.vi.size() ? other.vi[j] : 0);
            result.vi[i+j] = sum % 10;
            carry = sum / 10;
        }
    }
    while (!result.vi.empty() && result.vi.back() == 0)
        result.vi.pop_back();
    return result;
}

// Division operator
BigInt BigInt::operator/(const BigInt& other) const {
    if (other == BigInt(0))
        throw "Division by zero";
    
    BigInt result, current;
    for (int i = vi.size() - 1; i >= 0; i--) {
        current.vi.insert(current.vi.begin(), vi[i]);
        int x = 0, l = 0, r = 10;
        while (l <= r) {
            int m = (l + r) / 2;
            if (other * BigInt(m) <= current) {
                x = m;
                l = m + 1;
            } else {
                r = m - 1;
            }
        }
        result.vi.insert(result.vi.begin(), x);
        current = current - other * BigInt(x);
    }
    while (!result.vi.empty() && result.vi.back() == 0)
        result.vi.pop_back();
    return result;
}

// Modulo operator
BigInt BigInt::operator%(const BigInt& other) const {
    if (other == BigInt(0))
        throw "Modulo by zero";
    
    BigInt current;
    for (int i = vi.size() - 1; i >= 0; i--) {
        current.vi.insert(current.vi.begin(), vi[i]);
        int x = 0, l = 0, r = 10;
        while (l <= r) {
            int m = (l + r) / 2;
            if (other * BigInt(m) <= current) {
                x = m;
                l = m + 1;
            } else {
                r = m - 1;
            }
        }
        current = current - other * BigInt(x);
    }
    return current;
}

// Post-increment operator
BigInt BigInt::operator++(int) {
    BigInt temp = *this;
    *this = *this + 1;
    return temp;
}

// Pre-increment operator
BigInt BigInt::operator++() {
    *this = *this + 1;
    return *this;
}

// Equality operator
bool BigInt::operator==(const BigInt& other) const {
    return vi == other.vi;
}

// Less than or equal to operator
bool BigInt::operator<=(const BigInt& other) const {
    if (vi.size() != other.vi.size())
        return vi.size() < other.vi.size();
    for (int i = vi.size() - 1; i >= 0; i--) {
        if (vi[i] != other.vi[i])
            return vi[i] < other.vi[i];
    }
    return true;
}

// Print the BigInt
void BigInt::print() const {
    for (int i = vi.size() - 1; i >= 0; i--) {
        cout << static_cast<int>(vi[i]);
    }
}

// Return the number of digits
int BigInt::size() const {
    return vi.size();
}

// Compute Fibonacci sequence
BigInt BigInt::fibo() const {
    return fiboHelper(*this, 0, 1);
}

// Helper function for fibonacci computation
BigInt BigInt::fiboHelper(BigInt n, BigInt a, BigInt b) const {
    if (n == 0) return a;
    if (n == 1) return b;
    return fiboHelper(n - 1, b, a + b);
}

// Compute fractional
BigInt BigInt::fact() const {
    BigInt result = 1;
    for (BigInt i = 2; i <= *this; i = i + 1)
        result = result * i;
    return result;
}

// Output stream operator for BigInt
ostream& operator<<(ostream& os, const BigInt& bigint) {
    bigint.print();
    return os;
}

// Addition operator (int + BigInt)
BigInt operator+(int n, const BigInt& bigint) {
    return BigInt(n) + bigint;
}

// Unit test function
void testUnit() {
    int space = 10;
    cout << "\a\nTestUnit:\n" << flush;
    system("whoami");
    system("date");
    BigInt n1(25);
    BigInt s1("25");
    BigInt n2(1234);
    BigInt s2("1234");
    BigInt n3(n2);

    BigInt fibo(12345);
    BigInt fact(50);
    BigInt imax = INT_MAX;
    BigInt big("9223372036854775807");

    cout << "n1(int)    :" << setw(space) << n1 << endl;
    cout << "s1(str)    :" << setw(space) << s1 << endl;
    cout << "n2(int)    :" << setw(space) << n2 << endl;
    cout << "s2(str)    :" << setw(space) << s2 << endl;
    cout << "n3(n2)     :" << setw(space) << n3 << endl;
    cout << "fibo(12345):" << setw(space) << fibo << endl;
    cout << "fact(50)   :" << setw(space) << fact << endl;
    cout << "imax       :" << setw(space) << imax << endl;
    cout << "big        :" << setw(space) << big << endl;
    cout << "big.print(): ";
    big.print();
    cout << endl;

    cout << n2 << "/" << n1 << " = " << n2 / n1 << " rem " << n2 % n1 << endl;
    cout << "Fibo(" << fibo << ") = " << scientific << setprecision(4) << fibo.fibo() << "e" << fibo.size() << endl;
    cout << "fact(" << fact << ") = " << scientific << setprecision(4) << fact.fact() << endl;

    cout << "10 + n1 = " << 10 + n1 << endl;
    cout << "n1 + 10 = " << n1 + 10 << endl;

    cout << "(n1 == s1)? --> " << ((n1 == s1) ? "true" : "false") << endl;
    cout << "n1++ = ?  --> before:" << n1++ << " after:" << n1 << endl;
    cout << "++s1 = ?  --> before:" << ++s1 << " after:" << s1 << endl;

    cout << "s2 * big = ? --> " << s2 * big << endl;
    cout << "big * s2 = ? --> " << big * s2 << endl;
}

// Main function
int main() {
    testUnit(); // Run unit test
    return 0;   // Return 0 to indicate successful execution
}
