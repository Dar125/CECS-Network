// Muhammad Dar
// CECS-325-01
// Prog 5-bucketList
// I certify that this program is my own orginal work. I did not copy any part of this program from
// any other source. I further certify that I types each and every line of code in this program.


#include <iostream>
#include <vector>
#include <cstdlib>
#include <ctime>
#include <fstream>
#include <stdexcept> 

using namespace std;

long long globalSwapCount = 0; // Global counter for the swaps

class Bucket {
private:
    vector<int> v; // to store integers within a bucket

public:
    // Default constructor
    Bucket() {}

    // to create random numbers in the bukcet
    void generate(int size, int min, int max) {
        for (int i = 0; i < size; ++i) {
            v.push_back(min + rand() % (max - min + 1));
        }
    }

    // to sort the nubmers using bubble sort
    void sort() {
        for (size_t i = 0; i < v.size(); i++) {
            for (size_t j = 0; j < v.size() - i - 1; j++) {
                if (v[j] > v[j + 1]) {
                    swap(v[j], v[j + 1]);
                    globalSwapCount++; // Increment the swap count
                }
            }
        }
    }

    int size() {
        return v.size();
    }

    int atIndex(int index) {
        return v[index];
    }

    // to merge bucket 
    void merge(Bucket& b) {
        v.insert(v.end(), b.v.begin(), b.v.end());
        sort(); // sort the bombined elements
    }
};

// usage: $ bucketList 100 100 1000000 9000000
//          bucketList bucketCount bucketSize min max
int main(int argc, char *argv[]) {
    srand(time(0));

    if (argc < 5) {
        cerr << "Usage: " << argv[0] << " bucketCount bucketSize bucketMin bucketMax" << endl;
        return 1;
    }

    int bucketCount, bucketSize, bucketMin, bucketMax;
    try {
        // convert command line arguments from strings to integers        
        bucketCount = stoi(argv[1]);
        bucketSize = stoi(argv[2]);
        bucketMin = stoi(argv[3]);
        bucketMax = stoi(argv[4]);
    } catch (const invalid_argument& e) {
        // catch and handle conversions
        cerr << "Invalid number: " << e.what() << endl;
        return 1;
    } catch (const out_of_range& e) {
        // catch and handle cases where numbers are too large        
        cerr << "Number out of range: " << e.what() << endl;
        return 1;
    }

    // print the parsed command line arguments
    cout << "Bucket Count: " << bucketCount << endl;
    cout << "Bucket Size: " << bucketSize << endl;
    cout << "Bucket Min Value: " << bucketMin << endl;
    cout << "Bucket Max value: " << bucketMax << endl;

    vector<Bucket> list; // to store all buckets

    for (int i = 0; i < bucketCount; i++) {
        Bucket b; // to create a new bucket
        b.generate(bucketSize, bucketMin, bucketMax);
        list.push_back(b);
    }

    for (auto& bucket : list) {
        bucket.sort(); // sort each bucket
    }

    Bucket endGame; // create an empty bucket to store the merged result

    // merge all buckets into one
    while (!list.empty()) {
        endGame.merge(list[0]);
        list.erase(list.begin());
    }
    
    // open a file to store the output in the file called bucketList.out
    fstream out("bucketList.out", ios::out);
    for (int i = 0; i < endGame.size(); i++) {
        out << endGame.atIndex(i) << endl;
    }

    cout << "Global Swap Count: " << globalSwapCount << endl; // Output the global swap count
    cout << endl << "bucketList.out has " << bucketCount * bucketSize << " sorted numbers" << endl;

    return 0;
}
