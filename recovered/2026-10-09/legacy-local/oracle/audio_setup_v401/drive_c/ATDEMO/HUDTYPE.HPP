//++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
//              (c) Intelligent Games Ltd. 1995 All Rights Reserved
//
//              HUDTYPE.HPP
//
//              Provides types for HUD information.
//
//++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

#ifndef _HUDTYPE
#define _HUDTYPE

// These are all the possible substances objects in the world can be constructed out of.
// This information is used for HUD information only.
typedef enum {eMetal, eMetalCorroded, eParchment, eWood, eGrailstone, eGold, eSilver, eBone, eAnimalHorn,
                             eAlgae, eWater, eSteam, eStone, eGlass, eLeather, eGrain, eWax, eBlood, eInk,
                             eVolatileChemical, eWovenFibres, ePreciousStone} TSubstance;


// Max length of a message to display on the HUD.
typedef char THUDMessage[200];

// Additional information for each object that the HUD will display when scanned, advance scanned.
typedef struct
{
    float fWeight;      // kg
    u2 fPrice;              // $
    u2 fLength;         // cm
    u2 fWidth;           // cm  
    u2 fHeight;          // cm
    u2 fTemperature; // Degrees C
    TSubstance fSubstance;         //  Substance the object is made of. 
    THUDMessage fScanString;                    // First information string displayed by HUD when scanned.
    THUDMessage fAdvanceScanString;  // Advanced scan information string.
} TObjectHUDInformation;

    
extern ch * GetHUDMessage( u2 index );
/* Reads in a HUD message.  A pointer to the string is allocated and should
   be freed after use. */
   
#endif


